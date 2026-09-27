"""Domain entities and value objects for the task service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class User:
    """Represents a registered enterprise user in the system."""

    id: str
    email: str
    role: str = "employee"
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert user entity to serializable dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
        }


@dataclass(frozen=True)
class TaskShare:
    """Represents shared access permissions granted on a task."""

    user_id: str
    permission: str  # "view" or "edit"

    def to_dict(self) -> dict[str, Any]:
        """Convert task share to serializable dictionary."""
        return {
            "user_id": self.user_id,
            "permission": self.permission,
        }


@dataclass(frozen=True)
class TaskHistory:
    """Immutable audit record of a mutation applied to a task."""

    task_id: str
    actor_id: str
    action: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    before: dict[str, Any] = field(default_factory=dict)
    after: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert task history record to serializable dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "actor_id": self.actor_id,
            "action": self.action,
            "before": self.before,
            "after": self.after,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class Notification:
    """In-app alert notification delivered to a user."""

    user_id: str
    title: str
    message: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str | None = None
    is_read: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert notification entity to serializable dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "title": self.title,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at,
        }


@dataclass
class Task:
    """Core task entity encapsulating lifecycle state and metadata."""

    title: str
    owner_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notes: str = ""
    status: str = "open"  # "open", "in_progress", "done"
    priority: str = "medium"  # "low", "medium", "high", "urgent"
    assignee_id: str | None = None
    is_deleted: bool = False
    deleted_at: str | None = None
    due_date: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    shares: list[TaskShare] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert task entity to serializable dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "notes": self.notes,
            "status": self.status,
            "priority": self.priority,
            "owner_id": self.owner_id,
            "assignee_id": self.assignee_id or self.owner_id,
            "is_deleted": self.is_deleted,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "shares": [s.to_dict() for s in self.shares],
        }
