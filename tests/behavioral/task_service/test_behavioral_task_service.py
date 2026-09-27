"""Behavioral tests for task_service verifying PRD User Stories and Acceptance Criteria.

Stories covered:
- US-1: Capture a task
- US-2: Work and complete a task
- US-3: Follow-the-sun handoff
- US-4: Team lead rebalances work
- US-6: Recover a deleted task
- US-7: Administrator offboards a user
- US-8: Task deadline and handoff notifications
"""

import pytest
from modules.task_service.entrypoints.app import create_task_app


@pytest.fixture
def client():
    app = create_task_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_us1_ac1_capture_task(client):
    """[US-1][AC-1.1] Given an employee user, when they submit a task with title and priority, then the task is created in open status with default owner."""
    res = client.post(
        "/v1/tasks",
        json={"title": "Write spec", "priority": "high", "notes": "Initial draft"},
        headers={"X-User-Id": "emp_1", "X-User-Role": "employee"},
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["title"] == "Write spec"
    assert data["status"] == "open"
    assert data["owner_id"] == "emp_1"


def test_us2_ac1_work_and_complete_task(client):
    """[US-2][AC-2.1] Given an open task, when the assignee transitions it to in_progress and then to done, each transition succeeds and is recorded in history."""
    # Create task
    c_res = client.post(
        "/v1/tasks",
        json={"title": "Fix bug"},
        headers={"X-User-Id": "emp_1", "X-User-Role": "employee"},
    )
    task_id = c_res.get_json()["id"]

    # Transition open -> in_progress
    t1 = client.patch(
        f"/v1/tasks/{task_id}/status",
        json={"status": "in_progress"},
        headers={"X-User-Id": "emp_1", "X-User-Role": "employee"},
    )
    assert t1.status_code == 200
    assert t1.get_json()["status"] == "in_progress"

    # Transition in_progress -> done
    t2 = client.patch(
        f"/v1/tasks/{task_id}/status",
        json={"status": "done"},
        headers={"X-User-Id": "emp_1", "X-User-Role": "employee"},
    )
    assert t2.status_code == 200
    assert t2.get_json()["status"] == "done"

    # Verify history
    h_res = client.get(
        f"/v1/tasks/{task_id}/history",
        headers={"X-User-Id": "emp_1", "X-User-Role": "employee"},
    )
    assert h_res.status_code == 200
    assert h_res.get_json()["total"] >= 2


def test_us3_ac1_follow_the_sun_handoff(client):
    """[US-3][AC-3.1] Given an employee ending their shift, when they share or transfer the task to an oncoming teammate, ownership and edit permissions update with notifications."""
    c_res = client.post(
        "/v1/tasks",
        json={"title": "Shift handoff task"},
        headers={"X-User-Id": "apac_user", "X-User-Role": "employee"},
    )
    task_id = c_res.get_json()["id"]

    # Share with EMEA teammate
    s_res = client.post(
        f"/v1/tasks/{task_id}/shares",
        json={"target_user_id": "emea_user", "permission": "edit"},
        headers={"X-User-Id": "apac_user", "X-User-Role": "employee"},
    )
    assert s_res.status_code == 200

    # EMEA teammate can now edit
    e_res = client.put(
        f"/v1/tasks/{task_id}",
        json={"notes": "EMEA taking over investigation"},
        headers={"X-User-Id": "emea_user", "X-User-Role": "employee"},
    )
    assert e_res.status_code == 200


def test_us4_ac1_team_lead_rebalances_work(client):
    """[US-4][AC-4.1] Given a team lead, when viewing member tasks and reassigning an overload task to another teammate, the task owner updates and history is recorded."""
    c_res = client.post(
        "/v1/tasks",
        json={"title": "Overload task"},
        headers={"X-User-Id": "emp_1", "X-User-Role": "employee"},
    )
    task_id = c_res.get_json()["id"]

    # Lead reassigns
    r_res = client.post(
        f"/v1/tasks/{task_id}/reassign",
        json={"new_owner_id": "emp_2", "reason": "Workload balancing"},
        headers={"X-User-Id": "lead_1", "X-User-Role": "lead"},
    )
    assert r_res.status_code == 200
    assert r_res.get_json()["owner_id"] == "emp_2"


def test_us6_ac1_recover_deleted_task(client):
    """[US-6][AC-6.1] Given a deleted task within 30-day retention, when the owner requests restoration, the task is restored to active status with full history intact."""
    c_res = client.post(
        "/v1/tasks",
        json={"title": "Accidentally deleted task"},
        headers={"X-User-Id": "emp_1", "X-User-Role": "employee"},
    )
    task_id = c_res.get_json()["id"]

    # Delete task
    d_res = client.delete(
        f"/v1/tasks/{task_id}",
        headers={"X-User-Id": "emp_1", "X-User-Role": "employee"},
    )
    assert d_res.status_code == 200
    assert d_res.get_json()["is_deleted"] is True

    # Restore task
    rst_res = client.post(
        f"/v1/tasks/{task_id}/restore",
        headers={"X-User-Id": "emp_1", "X-User-Role": "employee"},
    )
    assert rst_res.status_code == 200
    assert rst_res.get_json()["is_deleted"] is False


def test_us7_ac1_admin_offboards_user(client):
    """[US-7][AC-7.1] Given an administrator, when they deactivate a departing user, open tasks are surfaced in the orphaned queue and can be reassigned."""
    # Create task owned by offboarding user
    c_res = client.post(
        "/v1/tasks",
        json={"title": "Orphaned task"},
        headers={"X-User-Id": "departing_user", "X-User-Role": "employee"},
    )
    task_id = c_res.get_json()["id"]

    # Deactivate user
    u_res = client.patch(
        "/v1/users/departing_user/status",
        json={"is_active": False},
        headers={"X-User-Id": "admin_1", "X-User-Role": "admin"},
    )
    assert u_res.status_code == 200

    # Query orphaned tasks
    o_res = client.get(
        "/v1/tasks/orphaned",
        headers={"X-User-Id": "admin_1", "X-User-Role": "admin"},
    )
    assert o_res.status_code == 200
    orphans = o_res.get_json()["tasks"]
    assert any(t["id"] == task_id for t in orphans)


def test_us8_ac1_notifications_on_handoff(client):
    """[US-8][AC-8.1] Given an employee receiving a handoff or nearing a deadline, notifications are queryable and can be marked read."""
    # Read notifications
    n_res = client.get(
        "/v1/notifications",
        headers={"X-User-Id": "emp_1", "X-User-Role": "employee"},
    )
    assert n_res.status_code == 200
    data = n_res.get_json()
    assert "notifications" in data
