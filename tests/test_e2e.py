"""
End-to-end tests for the ticket processing system.

These tests require the full stack to be running:
    docker compose up -d

Run with:
    pytest tests/test_e2e.py -v -s
"""

import time
import uuid
import httpx
import pytest

# Base URL for the API (assumes docker compose is running)
BASE_URL = "http://localhost:8000"

# Timeout for ticket processing (seconds)
PROCESSING_TIMEOUT = 120
POLL_INTERVAL = 2


@pytest.fixture
def api_client():
    """Create an HTTP client for API requests."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
def unique_ticket_data():
    """Generate unique ticket data to avoid idempotency conflicts."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "subject": f"Test ticket {unique_id}",
        "body": f"This is a test ticket body for E2E testing. ID: {unique_id}",
        "customer_id": f"test_customer_{unique_id}",
    }


class TestHealthCheck:
    """Test that the system is healthy before running E2E tests."""

    def test_api_is_healthy(self, api_client):
        """Verify API service is running and healthy."""
        response = api_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"
        assert data["queue"] == "healthy"


class TestFullTicketLifecycle:
    """Test the complete ticket processing lifecycle."""

    def test_ticket_creation_to_completion(self, api_client, unique_ticket_data):
        """
        E2E test: Create ticket → Process → Complete

        Steps:
        1. POST /tickets - Create new ticket
        2. GET /tickets/{id} - Poll until completed
        3. Verify result structure
        4. GET /tickets/{id}/events - Verify all workflow steps
        """
        # Step 1: Create ticket
        print(f"\n[E2E] Creating ticket: {unique_ticket_data['subject']}")
        response = api_client.post("/tickets", json=unique_ticket_data)

        assert response.status_code == 201, f"Failed to create ticket: {response.text}"
        create_data = response.json()

        ticket_id = create_data["ticket_id"]
        assert ticket_id is not None
        assert create_data["status"] == "pending"
        print(f"[E2E] Ticket created: {ticket_id}")

        # Step 2: Poll until completion
        print(f"[E2E] Polling for completion (timeout: {PROCESSING_TIMEOUT}s)...")
        start_time = time.time()
        final_status = None
        ticket_data = None

        while time.time() - start_time < PROCESSING_TIMEOUT:
            response = api_client.get(f"/tickets/{ticket_id}")
            assert response.status_code == 200

            ticket_data = response.json()
            final_status = ticket_data["status"]

            if final_status in ("completed", "failed_permanent"):
                break

            print(f"[E2E] Status: {final_status}, waiting...")
            time.sleep(POLL_INTERVAL)

        elapsed = time.time() - start_time
        print(f"[E2E] Final status: {final_status} (took {elapsed:.1f}s)")

        # Step 3: Verify completion
        assert final_status == "completed", f"Ticket did not complete. Status: {final_status}"
        assert ticket_data["result"] is not None, "Result should not be None"

        result = ticket_data["result"]
        assert "final_response" in result, "Result should have final_response"
        assert "classification" in result, "Result should have classification"
        assert result["final_response"] is not None, "final_response should not be None"

        print(f"[E2E] Classification: {result.get('classification')}")
        print(f"[E2E] Response preview: {result['final_response'][:100]}...")

        # Step 4: Verify events
        response = api_client.get(f"/tickets/{ticket_id}/events")
        assert response.status_code == 200

        events = response.json()
        assert len(events) > 0, "Should have events"

        event_types = [e["event_type"] for e in events]
        print(f"[E2E] Event types: {event_types}")

        # Verify workflow steps were recorded
        step_events = [e for e in events if e["event_type"] == "step_complete"]
        step_names = [e["step_name"] for e in step_events]
        print(f"[E2E] Completed steps: {step_names}")

        expected_steps = ["classify", "extract", "research", "draft", "review", "finalize"]
        for step in expected_steps:
            assert step in step_names, f"Missing step: {step}"

        print("[E2E] All workflow steps completed successfully!")

    def test_duplicate_ticket_is_idempotent(self, api_client, unique_ticket_data):
        """Test that submitting the same ticket twice returns the existing ticket."""
        # Create first ticket
        response1 = api_client.post("/tickets", json=unique_ticket_data)
        assert response1.status_code == 201
        ticket_id_1 = response1.json()["ticket_id"]

        # Submit same ticket again
        response2 = api_client.post("/tickets", json=unique_ticket_data)
        # Should return 201 but with same ticket ID (idempotent)
        assert response2.status_code == 201
        ticket_id_2 = response2.json()["ticket_id"]

        assert ticket_id_1 == ticket_id_2, "Duplicate ticket should return same ID"
        print(f"[E2E] Idempotency verified: {ticket_id_1}")


class TestTicketValidation:
    """Test input validation."""

    def test_missing_subject_returns_422(self, api_client):
        """Test that missing subject returns validation error."""
        response = api_client.post(
            "/tickets",
            json={"body": "Test body", "customer_id": "cust1"},
        )
        assert response.status_code == 422

    def test_missing_body_returns_422(self, api_client):
        """Test that missing body returns validation error."""
        response = api_client.post(
            "/tickets",
            json={"subject": "Test subject", "customer_id": "cust1"},
        )
        assert response.status_code == 422

    def test_missing_customer_id_returns_422(self, api_client):
        """Test that missing customer_id returns validation error."""
        response = api_client.post(
            "/tickets",
            json={"subject": "Test subject", "body": "Test body"},
        )
        assert response.status_code == 422


class TestRequestTracing:
    """Test request ID propagation."""

    def test_response_includes_request_id(self, api_client):
        """Test that responses include X-Request-ID header."""
        response = api_client.get("/health")
        assert "x-request-id" in response.headers

    def test_custom_request_id_preserved(self, api_client):
        """Test that custom X-Request-ID is preserved."""
        custom_id = f"test-{uuid.uuid4()}"
        response = api_client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.headers["x-request-id"] == custom_id


class TestMetrics:
    """Test metrics endpoint."""

    def test_metrics_returns_prometheus_format(self, api_client):
        """Test that /metrics returns Prometheus format."""
        response = api_client.get("/metrics")
        assert response.status_code == 200

        content = response.text
        # Check for expected metrics
        assert "tickets_created_total" in content or "http_request_duration" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
