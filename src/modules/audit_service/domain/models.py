"""Domain entities and value objects for the audit service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    """Represents an immutable, tamper-evident audit event."""

    actor_id: str
    action: str
    target_type: str
    target_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the audit event to a serializable dictionary."""
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass(frozen=True)
class AuditQuery:
    """Encapsulates filter parameters for searching audit records."""

    actor_id: str | None = None
    task_id: str | None = None
    action: str | None = None
    start_time: str | None = None
    end_time: str | None = None

    def matches(self, event: AuditEvent) -> bool:
        """Check whether a given audit event satisfies this query criteria."""
        if self.actor_id is not None and event.actor_id != self.actor_id:
            return False
        if self.action is not None and event.action != self.action:
            return False
        if self.task_id is not None:
            if event.target_type == "task" and event.target_id != self.task_id:
                return False
            if event.target_type != "task" and event.context.get("task_id") != self.task_id:
                return False
        if self.start_time is not None and event.timestamp < self.start_time:
            return False
        if self.end_time is not None and event.timestamp > self.end_time:
            return False
        return True


@dataclass(frozen=True)
class AuditExport:
    """Represents an immutable export bundle of audit events."""

    export_id: str
    record_count: int
    generated_at: str
    records: list[AuditEvent]

    def to_dict(self) -> dict[str, Any]:
        """Convert the export bundle to a serializable dictionary."""
        return {
            "export_id": self.export_id,
            "record_count": self.record_count,
            "generated_at": self.generated_at,
            "records": [r.to_dict() for r in self.records],
        }
