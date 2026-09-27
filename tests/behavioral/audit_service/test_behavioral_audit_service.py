"""Behavioral tests for audit_service verifying PRD User Stories and Acceptance Criteria.

Stories covered:
- US-5: Auditor investigates and exports trail
- US-6: Recover a deleted task (audit verification)
- US-7: Administrator offboards a user (audit verification)
"""

import pytest
from modules.audit_service.entrypoints.app import create_audit_app


@pytest.fixture
def client():
    app = create_audit_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_us5_ac1_auditor_search_events(client):
    """[US-5][AC-5.1] Given an auditor user, when they search audit logs by actor or task ID, then matching immutable events are returned."""
    client.post(
        "/v1/audit/events",
        json={"actor_id": "emp_1", "action": "task_updated", "target_type": "task", "target_id": "t1"},
        headers={"X-User-Role": "employee"},
    )
    res = client.get("/v1/audit/events?actor_id=emp_1", headers={"X-User-Role": "auditor"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] >= 1
    assert data["events"][0]["actor_id"] == "emp_1"


def test_us5_ac2_auditor_export_trail(client):
    """[US-5][AC-5.2] Given an auditor user, when they request an audit export, then an immutable export batch with record count and timestamps is generated."""
    res = client.post(
        "/v1/audit/export",
        json={"actor_id": "emp_1"},
        headers={"X-User-Role": "auditor"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "export_id" in data
    assert "records" in data


def test_us6_ac1_audit_log_for_restored_task(client):
    """[US-6][AC-6.1] Given a task that was restored, when searching audit records, then a task_restored audit event is verified."""
    client.post(
        "/v1/audit/events",
        json={"actor_id": "emp_2", "action": "task_restored", "target_type": "task", "target_id": "t2"},
        headers={"X-User-Role": "employee"},
    )
    res = client.get("/v1/audit/events?action=task_restored", headers={"X-User-Role": "auditor"})
    assert res.status_code == 200
    data = res.get_json()
    assert any(e["action"] == "task_restored" for e in data["events"])


def test_us7_ac1_audit_log_for_user_offboarding(client):
    """[US-7][AC-7.1] Given an administrator offboarding a user, when searching audit records, then a user_deactivated audit event is verified."""
    client.post(
        "/v1/audit/events",
        json={"actor_id": "admin_1", "action": "user_deactivated", "target_type": "user", "target_id": "u3"},
        headers={"X-User-Role": "admin"},
    )
    res = client.get("/v1/audit/events?action=user_deactivated", headers={"X-User-Role": "auditor"})
    assert res.status_code == 200
    data = res.get_json()
    assert any(e["action"] == "user_deactivated" for e in data["events"])
