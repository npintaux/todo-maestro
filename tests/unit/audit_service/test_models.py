"""Unit tests for audit_service domain models."""

from modules.audit_service.domain.models import AuditEvent, AuditExport, AuditQuery


def test_audit_event_creation_and_to_dict():
    """Verify AuditEvent serialization and default properties."""
    event = AuditEvent(
        actor_id="user_1",
        action="task_created",
        target_type="task",
        target_id="task_1",
        context={"title": "Test"},
    )
    d = event.to_dict()
    assert d["actor_id"] == "user_1"
    assert d["action"] == "task_created"
    assert d["target_type"] == "task"
    assert d["target_id"] == "task_1"
    assert d["context"]["title"] == "Test"
    assert "timestamp" in d
    assert "id" in d


def test_audit_query_matching():
    """Verify AuditQuery filtering logic against various predicates."""
    event1 = AuditEvent(
        actor_id="user_1",
        action="task_created",
        target_type="task",
        target_id="task_1",
        timestamp="2026-01-01T10:00:00Z",
    )
    event2 = AuditEvent(
        actor_id="user_2",
        action="task_updated",
        target_type="user",
        target_id="u2",
        timestamp="2026-01-02T10:00:00Z",
        context={"task_id": "task_1"},
    )

    q1 = AuditQuery(actor_id="user_1")
    assert q1.matches(event1)
    assert not q1.matches(event2)

    q2 = AuditQuery(action="task_updated")
    assert not q2.matches(event1)
    assert q2.matches(event2)

    q3 = AuditQuery(task_id="task_1")
    assert q3.matches(event1)
    assert q3.matches(event2)

    event3 = AuditEvent(actor_id="u3", action="act", target_type="task", target_id="other_task")
    assert not q3.matches(event3)

    event4 = AuditEvent(actor_id="u4", action="act", target_type="user", target_id="u4", context={})
    assert not q3.matches(event4)

    q4 = AuditQuery(start_time="2026-01-01T12:00:00Z")
    assert not q4.matches(event1)
    assert q4.matches(event2)

    q5 = AuditQuery(end_time="2026-01-01T12:00:00Z")
    assert q5.matches(event1)
    assert not q5.matches(event2)


def test_audit_export_to_dict():
    """Verify AuditExport bundle serialization."""
    event = AuditEvent(
        actor_id="user_1",
        action="task_created",
        target_type="task",
        target_id="task_1",
    )
    export = AuditExport(
        export_id="exp-123",
        record_count=1,
        generated_at="2026-01-01T10:00:00Z",
        records=[event],
    )
    d = export.to_dict()
    assert d["export_id"] == "exp-123"
    assert d["record_count"] == 1
    assert len(d["records"]) == 1
