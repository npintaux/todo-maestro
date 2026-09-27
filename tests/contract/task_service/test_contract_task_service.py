"""Contract tests for task_service OpenAPI specification.

Validates that HTTP status codes documented in openapi.yaml are asserted:
200, 201, 400, 401, 403, 404, 500.
"""

import pytest
from modules.task_service.entrypoints.app import create_task_app


@pytest.fixture
def client():
    app = create_task_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_create_task_success_201(client):
    """Test POST /v1/tasks returns 201 Created."""
    response = client.post(
        "/v1/tasks",
        json={"title": "Test Task", "priority": "high"},
        headers={"X-User-Id": "u1", "X-User-Role": "employee"},
    )
    assert response.status_code == 201


def test_create_task_bad_request_400(client):
    """Test POST /v1/tasks returns 400 Bad Request on missing title."""
    response = client.post(
        "/v1/tasks",
        json={},
        headers={"X-User-Id": "u1", "X-User-Role": "employee"},
    )
    assert response.status_code == 400


def test_task_unauthorized_401(client):
    """Test GET /v1/tasks returns 401 Unauthorized without auth headers."""
    response = client.get("/v1/tasks", headers={"X-Unauthenticated": "1"})
    assert response.status_code == 401


def test_task_forbidden_403(client):
    """Test accessing or modifying non-owned task returns 403 Forbidden."""
    response = client.get(
        "/v1/tasks/task_forbidden_id",
        headers={"X-User-Id": "u_unauthorized", "X-User-Role": "employee"},
    )
    assert response.status_code == 403


def test_task_not_found_404(client):
    """Test GET /v1/tasks/{id} returns 404 Not Found for non-existent task."""
    response = client.get(
        "/v1/tasks/non_existent_999",
        headers={"X-User-Id": "u1", "X-User-Role": "employee"},
    )
    assert response.status_code == 404


def test_list_tasks_success_200(client):
    """Test GET /v1/tasks returns 200 OK."""
    response = client.get(
        "/v1/tasks",
        headers={"X-User-Id": "u1", "X-User-Role": "employee"},
    )
    assert response.status_code == 200


def test_task_internal_server_error_500(client):
    """Test endpoints return 500 Internal Server Error on unexpected datastore exception."""
    response = client.get(
        "/v1/tasks?force_error=1",
        headers={"X-User-Id": "u1", "X-User-Role": "employee"},
    )
    assert response.status_code == 500
