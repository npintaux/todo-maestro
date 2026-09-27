"""Unit tests for unified production WSGI entrypoint src/main.py."""

from __future__ import annotations

import pytest
from src.main import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.get_json() == {"status": "healthy", "service": "taskflow"}


def test_root_redirect(client):
    res = client.get("/")
    assert res.status_code == 302
    assert "/tasks" in res.headers["Location"]


def test_audit_proxy(client):
    # Record event
    payload = {
        "actor_id": "auditor_1",
        "action": "task_exported",
        "target_type": "task",
        "target_id": "task_123",
        "context": {"reason": "compliance"},
    }
    create_res = client.post(
        "/v1/audit/events",
        json=payload,
        headers={"X-User-Role": "auditor", "X-User-Id": "auditor_1"},
    )
    assert create_res.status_code == 201
    event = create_res.get_json()
    event_id = event["id"]

    # Search events with query parameters (covering line 43)
    search_res = client.get(
        "/v1/audit/events?action=task_exported",
        headers={"X-User-Role": "auditor", "X-User-Id": "auditor_1"},
    )
    assert search_res.status_code == 200
    assert search_res.get_json()["total"] >= 1

    # Export events
    export_res = client.post(
        "/v1/audit/export",
        json={"actor_id": "auditor_1"},
        headers={"X-User-Role": "auditor", "X-User-Id": "auditor_1"},
    )
    assert export_res.status_code == 200
    bundle = export_res.get_json()
    assert "records" in bundle
    assert "record_count" in bundle
