"""In-memory implementation of the audit repository for testing and standalone execution."""

from __future__ import annotations

from modules.audit_service.domain.models import AuditEvent, AuditQuery
from modules.audit_service.domain.repository import AuditRepository


class InMemoryAuditRepository(AuditRepository):
    """In-memory append-only audit log storage."""

    def __init__(self) -> None:
        """Initialize empty audit storage list."""
        self._events: list[AuditEvent] = []

    def save(self, event: AuditEvent) -> None:
        """Append an immutable audit event to the in-memory log.

        Args:
            event: The audit event to store.
        """
        self._events.append(event)

    def search(self, query: AuditQuery) -> list[AuditEvent]:
        """Filter in-memory audit records according to query constraints.

        Args:
            query: Filter constraints.

        Returns:
            List of matching events.
        """
        return [e for e in self._events if query.matches(e)]

    def all(self) -> list[AuditEvent]:
        """Return all recorded audit events.

        Returns:
            List of all events in chronological order.
        """
        return list(self._events)
