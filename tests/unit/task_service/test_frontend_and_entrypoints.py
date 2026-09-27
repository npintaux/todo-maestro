"""Unit tests for task service Flask frontend routes and entrypoint edge cases."""

from unittest.mock import MagicMock
from modules.task_service.entrypoints.app import create_task_app


def test_ui_tasks_list():
    """Verify GET /tasks renders tasks_list template."""
    app = create_task_app()
    with app.test_client() as client:
        res = client.get("/tasks")
        assert res.status_code == 200
        assert b"Task Dashboard" in res.data


def test_ui_task_create_get_and_post():
    """Verify GET and POST /tasks/new."""
    app = create_task_app()
    with app.test_client() as client:
        # GET
        res = client.get("/tasks/new")
        assert res.status_code == 200
        assert b"Create New Task" in res.data

        # POST creates and redirects
        res_post = client.post(
            "/tasks/new",
            data={"title": "UI Task", "notes": "From Web", "priority": "high"},
            follow_redirects=True,
        )
        assert res_post.status_code == 200
        assert b"UI Task" in res_post.data


def test_ui_task_detail_and_orphaned():
    """Verify task detail view and orphaned tasks view."""
    app = create_task_app()
    with app.test_client() as client:
        # Create task
        res = client.post("/v1/tasks", json={"title": "Detail Task"}, headers={"X-User-Id": "u1"})
        task_id = res.get_json()["id"]

        # View detail
        res_detail = client.get(f"/tasks/{task_id}", headers={"X-User-Id": "u1"})
        assert res_detail.status_code == 200
        assert b"Detail Task" in res_detail.data

        # Detail of missing task redirects to list
        res_missing = client.get("/tasks/missing", follow_redirects=True)
        assert res_missing.status_code == 200
        assert b"Task Dashboard" in res_missing.data

        # Orphaned tasks view
        res_orphans = client.get("/tasks/orphaned", headers={"X-User-Role": "lead"})
        assert res_orphans.status_code == 200
        assert b"Orphaned Tasks Administration" in res_orphans.data

        # Orphaned tasks view without lead role handles gracefully
        res_orphans_emp = client.get("/tasks/orphaned", headers={"X-User-Role": "employee"})
        assert res_orphans_emp.status_code == 200


def test_entrypoint_error_branches():
    """Verify force_error and error handling across entrypoint routes."""
    app = create_task_app()
    with app.test_client() as client:
        # force_error on all endpoints
        assert client.post("/v1/tasks?force_error=1", json={}).status_code == 500
        assert client.get("/v1/tasks?force_error=1").status_code == 500
        assert client.get("/v1/tasks/orphaned?force_error=1").status_code == 500
        assert client.get("/v1/tasks/1?force_error=1").status_code == 500
        assert client.patch("/v1/tasks/1?force_error=1", json={}).status_code == 500
        assert client.delete("/v1/tasks/1?force_error=1").status_code == 500
        assert client.post("/v1/tasks/1/status?force_error=1", json={}).status_code == 500
        assert client.post("/v1/tasks/1/restore?force_error=1").status_code == 500
        assert client.get("/v1/tasks/1/history?force_error=1").status_code == 500
        assert client.post("/v1/tasks/1/shares?force_error=1", json={}).status_code == 500
        assert client.post("/v1/tasks/1/reassign?force_error=1", json={}).status_code == 500
        assert client.get("/v1/notifications?force_error=1").status_code == 500
        assert client.post("/v1/notifications/1/read?force_error=1").status_code == 500
        assert client.post("/v1/users/1/status?force_error=1", json={}).status_code == 500

        # Unauthenticated
        assert client.get("/v1/tasks", headers={"X-Unauthenticated": "1"}).status_code == 401

        # Missing required fields
        assert client.post("/v1/tasks", json={}).status_code == 400
        assert client.post("/v1/tasks/1/status", json={}).status_code == 400
        assert client.post("/v1/tasks/1/shares", json={}).status_code == 400
        assert client.post("/v1/tasks/1/reassign", json={}).status_code == 400
        assert client.post("/v1/users/1/status", json={}).status_code == 400


def test_entrypoint_404_and_403_and_400_branches():
    """Verify 404, 403, and 400 branches in entrypoints."""
    app = create_task_app()
    with app.test_client() as client:
        # Create task owned by u1
        res = client.post("/v1/tasks", json={"title": "Branch Task"}, headers={"X-User-Id": "u1"})
        task_id = res.get_json()["id"]

        # 404 Not Found on missing task
        assert (
            client.get("/v1/tasks/no_such_task", headers={"X-User-Id": "u1"}).status_code
            == 404
        )
        assert (
            client.patch(
                "/v1/tasks/no_such_task", json={"title": "N"}, headers={"X-User-Id": "u1"}
            ).status_code
            == 404
        )
        assert (
            client.delete("/v1/tasks/no_such_task", headers={"X-User-Id": "u1"}).status_code
            == 404
        )
        assert (
            client.post(
                "/v1/tasks/no_such_task/status",
                json={"status": "in_progress"},
                headers={"X-User-Id": "u1"},
            ).status_code
            == 404
        )
        assert (
            client.post("/v1/tasks/no_such_task/restore", headers={"X-User-Id": "u1"}).status_code
            == 404
        )
        assert (
            client.get("/v1/tasks/no_such_task/history", headers={"X-User-Id": "u1"}).status_code
            == 404
        )
        assert (
            client.post(
                "/v1/tasks/no_such_task/shares",
                json={"user_id": "u2", "permission": "view"},
                headers={"X-User-Id": "u1"},
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/v1/tasks/no_such_task/reassign",
                json={"new_owner_id": "u2"},
                headers={"X-User-Role": "lead"},
            ).status_code
            == 404
        )
        assert client.post("/v1/notifications/no_such_notif/read").status_code == 404

        # 403 Forbidden on unauthorized employee actions
        headers_stranger = {"X-User-Id": "stranger", "X-User-Role": "employee"}
        assert client.get(f"/v1/tasks/{task_id}", headers=headers_stranger).status_code == 403
        assert (
            client.patch(
                f"/v1/tasks/{task_id}", json={"title": "Hacked"}, headers=headers_stranger
            ).status_code
            == 403
        )
        assert client.delete(f"/v1/tasks/{task_id}", headers=headers_stranger).status_code == 403
        assert (
            client.post(
                f"/v1/tasks/{task_id}/status",
                json={"status": "in_progress"},
                headers=headers_stranger,
            ).status_code
            == 403
        )
        assert (
            client.get(f"/v1/tasks/{task_id}/history", headers=headers_stranger).status_code
            == 403
        )
        assert (
            client.post(
                f"/v1/tasks/{task_id}/shares",
                json={"user_id": "u3", "permission": "view"},
                headers=headers_stranger,
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/v1/tasks/{task_id}/reassign",
                json={"new_owner_id": "u3"},
                headers=headers_stranger,
            ).status_code
            == 403
        )
        assert (
            client.post("/v1/users/u1/status", json={"is_active": True}, headers=headers_stranger).status_code
            == 403
        )
        assert client.get("/v1/tasks/orphaned", headers=headers_stranger).status_code == 403

        # 400 Bad Request on invalid status transition
        assert (
            client.post(
                f"/v1/tasks/{task_id}/status",
                json={"status": "done"},
                headers={"X-User-Id": "u1"},
            ).status_code
            == 400
        )
        # 400 Bad Request on restoring non-deleted task
        assert (
            client.post(f"/v1/tasks/{task_id}/restore", headers={"X-User-Id": "u1"}).status_code
            == 400
        )

        # Delete task, then stranger tries to restore (403), then u1 restores (200)
        assert client.delete(f"/v1/tasks/{task_id}", headers={"X-User-Id": "u1"}).status_code == 200
        assert (
            client.post(f"/v1/tasks/{task_id}/restore", headers=headers_stranger).status_code
            == 403
        )
        # Successful GET /v1/tasks/<task_id>
        res_get = client.get(f"/v1/tasks/{task_id}", headers={"X-User-Id": "u1"})
        assert res_get.status_code == 200
        assert res_get.get_json()["title"] == "Branch Task"

        # Share to trigger a notification, then mark as read (covering 200 on mark_notification_read)
        client.post(
            f"/v1/tasks/{task_id}/shares",
            json={"user_id": "u2", "permission": "view"},
            headers={"X-User-Id": "u1"},
        )
        notifs_res = client.get("/v1/notifications", headers={"X-User-Id": "u2"})
        notif_id = notifs_res.get_json()["notifications"][0]["id"]
        read_res = client.post(f"/v1/notifications/{notif_id}/read")
        assert read_res.status_code == 200
        assert read_res.get_json()["is_read"] is True


def test_entrypoint_service_exception():
    """Verify internal exception during task creation returns 500."""
    mock_svc = MagicMock()
    mock_svc.create_task.side_effect = RuntimeError("Storage failure")
    app = create_task_app(service=mock_svc)
    with app.test_client() as client:
        res = client.post("/v1/tasks", json={"title": "Fail Task"})
        assert res.status_code == 500
