"""Unit tests for audit service Flask entrypoints covering edge cases."""

from unittest.mock import MagicMock
from modules.audit_service.entrypoints.app import create_audit_app


def test_post_events_force_error():
    """Verify force_error returns 500 on POST /v1/audit/events."""
    app = create_audit_app()
    with app.test_client() as client:
        res = client.post("/v1/audit/events?force_error=1", json={})
        assert res.status_code == 500


def test_post_export_force_error():
    """Verify force_error returns 500 on POST /v1/audit/export."""
    app = create_audit_app()
    with app.test_client() as client:
        res = client.post(
            "/v1/audit/export?force_error=1",
            headers={"X-User-Role": "auditor"},
            json={},
        )
        assert res.status_code == 500


def test_post_export_forbidden():
    """Verify non-auditor receives 403 on POST /v1/audit/export."""
    app = create_audit_app()
    with app.test_client() as client:
        res = client.post("/v1/audit/export", headers={"X-User-Role": "guest"}, json={})
        assert res.status_code == 403


def test_post_events_internal_exception():
    """Verify exception handling during event recording returns 500."""
    mock_svc = MagicMock()
    mock_svc.record_event.side_effect = RuntimeError("Datastore connection dropped")
    app = create_audit_app(service=mock_svc)
    with app.test_client() as client:
        res = client.post(
            "/v1/audit/events",
            json={"actor_id": "u", "action": "a", "target_type": "t", "target_id": "i"},
        )
        assert res.status_code == 500
