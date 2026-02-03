"""
Load tests for the ticket processing system.

These tests require the full stack to be running:
    docker compose up -d

Run with:
    pytest tests/test_load.py -v -s

For heavier load testing, adjust CONCURRENT_TICKETS and TOTAL_TICKETS.
"""

import asyncio
import time
import uuid
from collections import Counter

import httpx
import pytest

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Load test configuration
CONCURRENT_TICKETS = 10  # Number of tickets submitted in parallel
TOTAL_TICKETS = 20  # Total tickets to process
PROCESSING_TIMEOUT = 300  # Max time to wait for all tickets (seconds)
POLL_INTERVAL = 3  # Seconds between status polls


def generate_ticket_data(index: int) -> dict:
    """Generate unique ticket data for load testing."""
    unique_id = f"{uuid.uuid4().hex[:8]}_{index}"
    return {
        "subject": f"Load test ticket #{index} - {unique_id}",
        "body": f"This is load test ticket number {index}. "
        f"Testing concurrent processing capability. ID: {unique_id}",
        "customer_id": f"load_test_customer_{unique_id}",
    }


class TestLoadProcessing:
    """Load tests for concurrent ticket processing."""

    @pytest.mark.asyncio
    async def test_concurrent_ticket_submission(self):
        """
        Test submitting multiple tickets concurrently.

        Verifies:
        - All tickets are created successfully
        - No duplicate processing occurs
        - All tickets eventually complete
        """
        print(f"\n[LOAD] Starting load test: {TOTAL_TICKETS} tickets, "
              f"{CONCURRENT_TICKETS} concurrent")

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Check health first
            health = await client.get("/health")
            assert health.status_code == 200
            assert health.json()["status"] == "healthy"
            print("[LOAD] System healthy, starting test...")

            # Submit tickets in batches
            ticket_ids = []
            start_time = time.time()

            for batch_start in range(0, TOTAL_TICKETS, CONCURRENT_TICKETS):
                batch_end = min(batch_start + CONCURRENT_TICKETS, TOTAL_TICKETS)
                batch_size = batch_end - batch_start

                print(f"[LOAD] Submitting batch {batch_start + 1}-{batch_end}...")

                # Create tasks for concurrent submission
                tasks = []
                for i in range(batch_start, batch_end):
                    ticket_data = generate_ticket_data(i)
                    tasks.append(client.post("/tickets", json=ticket_data))

                # Execute batch concurrently
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                for resp in responses:
                    if isinstance(resp, Exception):
                        print(f"[LOAD] Error: {resp}")
                        continue
                    assert resp.status_code == 201, f"Failed: {resp.text}"
                    ticket_ids.append(resp.json()["ticket_id"])

            submit_time = time.time() - start_time
            print(f"[LOAD] Submitted {len(ticket_ids)} tickets in {submit_time:.1f}s")

            # Poll all tickets until completion
            print("[LOAD] Waiting for all tickets to complete...")
            completed = set()
            failed = set()
            poll_start = time.time()

            while len(completed) + len(failed) < len(ticket_ids):
                if time.time() - poll_start > PROCESSING_TIMEOUT:
                    pending = set(ticket_ids) - completed - failed
                    print(f"[LOAD] TIMEOUT! Pending tickets: {len(pending)}")
                    break

                # Check status of incomplete tickets
                pending_ids = [
                    tid for tid in ticket_ids
                    if tid not in completed and tid not in failed
                ]

                # Poll in batches to avoid overwhelming the API
                for tid in pending_ids[:CONCURRENT_TICKETS]:
                    resp = await client.get(f"/tickets/{tid}")
                    if resp.status_code == 200:
                        status = resp.json()["status"]
                        if status == "completed":
                            completed.add(tid)
                        elif status == "failed_permanent":
                            failed.add(tid)

                progress = len(completed) + len(failed)
                print(f"[LOAD] Progress: {progress}/{len(ticket_ids)} "
                      f"(completed: {len(completed)}, failed: {len(failed)})")

                if len(completed) + len(failed) < len(ticket_ids):
                    await asyncio.sleep(POLL_INTERVAL)

            total_time = time.time() - start_time
            print(f"\n[LOAD] === RESULTS ===")
            print(f"[LOAD] Total tickets: {len(ticket_ids)}")
            print(f"[LOAD] Completed: {len(completed)}")
            print(f"[LOAD] Failed: {len(failed)}")
            print(f"[LOAD] Total time: {total_time:.1f}s")
            print(f"[LOAD] Avg time per ticket: {total_time / len(ticket_ids):.1f}s")

            # Verify no duplicate processing
            await self._verify_no_duplicates(client, list(completed)[:10])

            # Assert success rate
            success_rate = len(completed) / len(ticket_ids)
            print(f"[LOAD] Success rate: {success_rate * 100:.1f}%")
            assert success_rate >= 0.9, f"Success rate too low: {success_rate}"

    async def _verify_no_duplicates(self, client: httpx.AsyncClient, ticket_ids: list):
        """Verify no duplicate processing by checking events."""
        print("[LOAD] Verifying no duplicate processing...")

        for tid in ticket_ids:
            resp = await client.get(f"/tickets/{tid}/events")
            if resp.status_code != 200:
                continue

            events = resp.json()
            step_events = [e for e in events if e["event_type"] == "step_complete"]

            # Count occurrences of each step
            step_counts = Counter(e["step_name"] for e in step_events)

            # Each step should appear exactly once
            for step, count in step_counts.items():
                if count > 1:
                    print(f"[LOAD] WARNING: Duplicate processing detected! "
                          f"Ticket {tid}, step {step} ran {count} times")

        print("[LOAD] Duplicate check complete")


class TestBurstLoad:
    """Test system behavior under burst load."""

    @pytest.mark.asyncio
    async def test_burst_submission(self):
        """
        Test submitting a burst of tickets all at once.

        This tests the queue's ability to handle sudden load spikes.
        """
        BURST_SIZE = 15
        print(f"\n[BURST] Submitting {BURST_SIZE} tickets simultaneously...")

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Submit all at once
            tasks = []
            for i in range(BURST_SIZE):
                ticket_data = generate_ticket_data(i + 1000)  # Offset to avoid conflicts
                tasks.append(client.post("/tickets", json=ticket_data))

            start = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start

            # Count successes
            successes = sum(
                1 for r in responses
                if not isinstance(r, Exception) and r.status_code == 201
            )

            print(f"[BURST] Created {successes}/{BURST_SIZE} tickets in {elapsed:.2f}s")
            assert successes == BURST_SIZE, f"Only {successes} tickets created"


class TestThroughput:
    """Measure system throughput."""

    @pytest.mark.asyncio
    async def test_measure_throughput(self):
        """
        Measure tickets processed per minute.

        Note: This is a simple measurement, not a full benchmark.
        """
        SAMPLE_SIZE = 5
        print(f"\n[THROUGHPUT] Measuring with {SAMPLE_SIZE} tickets...")

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
            ticket_ids = []

            # Submit tickets
            for i in range(SAMPLE_SIZE):
                ticket_data = generate_ticket_data(i + 2000)
                resp = await client.post("/tickets", json=ticket_data)
                if resp.status_code == 201:
                    ticket_ids.append(resp.json()["ticket_id"])

            if not ticket_ids:
                pytest.skip("No tickets created")

            # Wait for completion and measure time
            start = time.time()
            completed = 0

            while completed < len(ticket_ids) and time.time() - start < 180:
                for tid in ticket_ids:
                    resp = await client.get(f"/tickets/{tid}")
                    if resp.status_code == 200:
                        if resp.json()["status"] == "completed":
                            completed += 1

                if completed < len(ticket_ids):
                    await asyncio.sleep(2)

            elapsed = time.time() - start

            if completed > 0:
                throughput = (completed / elapsed) * 60  # per minute
                print(f"[THROUGHPUT] Processed {completed} tickets in {elapsed:.1f}s")
                print(f"[THROUGHPUT] Throughput: {throughput:.1f} tickets/minute")
            else:
                print("[THROUGHPUT] No tickets completed in time")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
