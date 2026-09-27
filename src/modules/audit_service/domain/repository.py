"""Repository interface for audit event persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from modules.audit_service.domain.models import AuditEvent, AuditQuery


class AuditRepository(ABC):
    """Abstract interface defining persistence operations for immutable audit events."""

    @abstractmethod
    def save(self, event: AuditEvent) -> None:
        """Persist an immutable audit event to the datastore.

        Args:
            event: The audit event entity to persist.
        """
        raise NotImplementedError

    @abstractmethod
    def search(self, query: AuditQuery) -> list[AuditEvent]:
        """Search audit records matching the specified query filters.

        Args:
            query: The filter criteria.

        Returns:
            A list of matching audit events.
        """
        raise NotImplementedError

    @abstractmethod
    def all(self) -> list[AuditEvent]:
        """Retrieve all recorded audit events in chronological order.

        Returns:
            The complete sequence of audit events.
        """
        raise NotImplementedError
