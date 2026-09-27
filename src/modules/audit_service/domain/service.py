"""Business service orchestrating audit event recording, search, and export."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from modules.audit_service.domain.models import AuditEvent, AuditExport, AuditQuery
from modules.audit_service.domain.repository import AuditRepository


class AuditService:
    """Coordinates business rules, scoping, and exports for audit records."""

    def __init__(self, repository: AuditRepository) -> None:
        """Initialize service with an underlying audit repository.

        Args:
            repository: The persistence adapter.
        """
        self._repository = repository

    def record_event(
        self,
        actor_id: str,
        action: str,
        target_type: str,
        target_id: str,
        context: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Record an immutable audit event in the log.

        Args:
            actor_id: The user or system principal performing the action.
            action: The operation name (e.g., task_created, task_restored).
            target_type: Entity category (e.g., task, user).
            target_id: Unique identifier of the target entity.
            context: Optional dictionary containing metadata and diff details.

        Returns:
            The persisted AuditEvent instance.
        """
        if not actor_id or not action or not target_type or not target_id:
            raise ValueError("All audit event coordinates must be non-empty.")

        event = AuditEvent(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            context=context or {},
        )
        self._repository.save(event)
        return event

    def search_events(self, query: AuditQuery) -> list[AuditEvent]:
        """Search recorded audit events conforming to the filter query.

        Args:
            query: Filter constraints.

        Returns:
            Matching audit events.
        """
        return self._repository.search(query)

    def export_trail(self, query: AuditQuery) -> AuditExport:
        """Generate an immutable audit export bundle conforming to query filters.

        Args:
            query: Constraints defining export scope.

        Returns:
            An AuditExport object with batch identifier and event list.
        """
        matching = self._repository.search(query)
        return AuditExport(
            export_id=f"export-{uuid.uuid4()}",
            record_count=len(matching),
            generated_at=datetime.now(UTC).isoformat(),
            records=matching,
        )
