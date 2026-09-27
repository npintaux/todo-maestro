"""Unit tests for in-memory audit repository adapter."""

from modules.audit_service.adapters.memory_repository import InMemoryAuditRepository
from modules.audit_service.domain.models import AuditEvent, AuditQuery


def test_memory_repository_save_and_all():
    """Verify persisting and querying events in memory repository."""
    repo = InMemoryAuditRepository()
    e1 = AuditEvent(actor_id="u1", action="create", target_type="task", target_id="t1")
    e2 = AuditEvent(actor_id="u2", action="update", target_type="task", target_id="t2")

    repo.save(e1)
    repo.save(e2)

    assert repo.all() == [e1, e2]
    matching = repo.search(AuditQuery(actor_id="u1"))
    assert matching == [e1]
