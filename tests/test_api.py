"""Integration tests for the API layer."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("src.db.client.get_supabase_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_queue():
    """Mock RabbitMQ connection."""
    with patch("src.common.queue.QueueConnection") as mock_conn, \
         patch("src.common.queue.QueuePublisher") as mock_pub:
        mock_conn.return_value.connect.return_value = None
        mock_conn.return_value.close.return_value = None
        mock_pub.return_value.publish.return_value = None
        yield mock_pub


@pytest.fixture
def client(mock_supabase, mock_queue):
    """Create test client with mocked dependencies."""
    from src.api.main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_status(self, client, mock_supabase):
        """Test health endpoint returns expected structure."""
        # Mock DB query
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock()

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "queue" in data


class TestTicketCreation:
    def test_create_ticket_returns_ticket_id(self, client, mock_supabase, mock_queue):
        """Test creating a ticket returns a ticket ID."""
        # Mock DB operations
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": "test-uuid",
            "customer_id": "cust1",
            "subject": "Test",
            "body": "Help",
            "status": "pending",
            "result": None,
            "worker_id": None,
            "attempt_count": 0,
            "version": 1,
            "created_at": "2024-01-01T00:00:00Z",
            "started_at": None,
            "completed_at": None,
            "last_heartbeat": None,
        }])

        response = client.post(
            "/tickets",
            json={
                "subject": "Test",
                "body": "Help",
                "customer_id": "cust1",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "ticket_id" in data
        assert "status" in data
        assert data["status"] == "pending"

    def test_create_ticket_requires_subject(self, client):
        """Test that subject is required."""
        response = client.post(
            "/tickets",
            json={
                "body": "Help",
                "customer_id": "cust1",
            },
        )

        assert response.status_code == 422

    def test_create_ticket_requires_body(self, client):
        """Test that body is required."""
        response = client.post(
            "/tickets",
            json={
                "subject": "Test",
                "customer_id": "cust1",
            },
        )

        assert response.status_code == 422


class TestTicketRetrieval:
    def test_get_ticket_returns_ticket(self, client, mock_supabase):
        """Test getting a ticket by ID."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "customer_id": "cust1",
            "subject": "Test",
            "body": "Help",
            "status": "completed",
            "result": {"final_response": "Response here"},
            "worker_id": "worker-1",
            "attempt_count": 1,
            "version": 3,
            "created_at": "2024-01-01T00:00:00Z",
            "started_at": "2024-01-01T00:00:01Z",
            "completed_at": "2024-01-01T00:00:10Z",
            "last_heartbeat": "2024-01-01T00:00:09Z",
        }])

        response = client.get("/tickets/550e8400-e29b-41d4-a716-446655440000")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert data["status"] == "completed"

    def test_get_ticket_not_found(self, client, mock_supabase):
        """Test 404 for non-existent ticket."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        response = client.get("/tickets/550e8400-e29b-41d4-a716-446655440000")

        assert response.status_code == 404


class TestMetrics:
    def test_metrics_endpoint_exists(self, client):
        """Test that metrics endpoint returns Prometheus format."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"] or "text/plain" in str(response.headers)


class TestRequestTracing:
    def test_response_includes_request_id(self, client, mock_supabase):
        """Test that responses include X-Request-ID header."""
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock()

        response = client.get("/health")

        assert "X-Request-ID" in response.headers

    def test_custom_request_id_preserved(self, client, mock_supabase):
        """Test that custom X-Request-ID is preserved."""
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock()

        response = client.get("/health", headers={"X-Request-ID": "custom-123"})

        assert response.headers["X-Request-ID"] == "custom-123"
