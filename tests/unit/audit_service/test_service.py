"""Unit tests for audit_service domain service."""

import pytest
from modules.audit_service.adapters.memory_repository import InMemoryAuditRepository
from modules.audit_service.domain.models import AuditQuery
from modules.audit_service.domain.service import AuditService


def test_service_record_event():
    """Verify recording events through domain service."""
    repo = InMemoryAuditRepository()
    svc = AuditService(repo)

    event = svc.record_event(
        actor_id="u1",
        action="task_created",
        target_type="task",
        target_id="t1",
        context={"info": "val"},
    )
    assert event.actor_id == "u1"
    assert len(repo.all()) == 1


def test_service_record_event_empty_coordinates():
    """Verify validation error on empty coordinates."""
    repo = InMemoryAuditRepository()
    svc = AuditService(repo)

    with pytest.raises(ValueError, match="All audit event coordinates must be non-empty"):
        svc.record_event("", "action", "type", "id")


def test_service_search_and_export():
    """Verify search and export queries."""
    repo = InMemoryAuditRepository()
    svc = AuditService(repo)

    svc.record_event("u1", "task_created", "task", "t1")
    svc.record_event("u2", "task_deleted", "task", "t2")

    events = svc.search_events(AuditQuery(actor_id="u1"))
    assert len(events) == 1
    assert events[0].actor_id == "u1"

    export = svc.export_trail(AuditQuery(actor_id="u2"))
    assert export.record_count == 1
    assert export.records[0].actor_id == "u2"
