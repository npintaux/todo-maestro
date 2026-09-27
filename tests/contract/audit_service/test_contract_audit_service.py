"""Contract tests for audit_service OpenAPI specification.

Validates that HTTP status codes documented in openapi.yaml are asserted:
200, 201, 400, 401, 403, 500.
"""

import pytest
from modules.audit_service.entrypoints.app import create_audit_app


@pytest.fixture
def client():
    app = create_audit_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_record_audit_event_success_201(client):
    """Test POST /v1/audit/events returns 201 Created."""
    payload = {
        "actor_id": "user_123",
        "action": "task_created",
        "target_type": "task",
        "target_id": "task_abc",
        "context": {"priority": "high"},
    }
    response = client.post("/v1/audit/events", json=payload)
    assert response.status_code == 201


def test_record_audit_event_bad_request_400(client):
    """Test POST /v1/audit/events returns 400 on missing required fields."""
    response = client.post("/v1/audit/events", json={})
    assert response.status_code == 400


def test_audit_unauthorized_401(client):
    """Test endpoints return 401 Unauthorized when credentials are missing."""
    response = client.get("/v1/audit/events", headers={"X-Unauthenticated": "1"})
    assert response.status_code == 401


def test_audit_forbidden_403(client):
    """Test query returns 403 Forbidden when user lacks auditor role."""
    response = client.get("/v1/audit/events", headers={"X-User-Role": "employee"})
    assert response.status_code == 403


def test_search_audit_events_success_200(client):
    """Test GET /v1/audit/events returns 200 OK for auditor."""
    response = client.get("/v1/audit/events", headers={"X-User-Role": "auditor"})
    assert response.status_code == 200


def test_export_audit_trail_success_200(client):
    """Test POST /v1/audit/export returns 200 OK."""
    response = client.post(
        "/v1/audit/export",
        json={"actor_id": "user_123"},
        headers={"X-User-Role": "auditor"},
    )
    assert response.status_code == 200


def test_audit_internal_server_error_500(client):
    """Test endpoints return 500 on unexpected datastore exception."""
    response = client.get("/v1/audit/events?force_error=1", headers={"X-User-Role": "auditor"})
    assert response.status_code == 500
