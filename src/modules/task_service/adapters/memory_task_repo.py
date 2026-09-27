"""In-memory persistence adapter for tasks, history, notifications, and users."""

from __future__ import annotations

from modules.task_service.domain.models import (
    Notification,
    Task,
    TaskHistory,
    User,
)
from modules.task_service.domain.repository import TaskRepository


class InMemoryTaskRepository(TaskRepository):
    """In-memory storage adapter for tasks and related domain entities."""

    def __init__(self) -> None:
        """Initialize empty collections for entities."""
        self._tasks: dict[str, Task] = {}
        self._history: dict[str, list[TaskHistory]] = {}
        self._notifications: dict[str, list[Notification]] = {}
        self._users: dict[str, User] = {}

    def save_task(self, task: Task) -> None:
        """Store or update task entity.

        Args:
            task: Task to persist.
        """
        self._tasks[task.id] = task

    def get_task(self, task_id: str) -> Task | None:
        """Find task by ID.

        Args:
            task_id: Task identifier.

        Returns:
            Matching Task or None.
        """
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        owner_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        include_deleted: bool = False,
    ) -> list[Task]:
        """Filter tasks by owner, status, priority, and deletion state.

        Args:
            owner_id: Owner filter.
            status: Status filter.
            priority: Priority filter.
            include_deleted: Inactive/soft-deleted flag.

        Returns:
            List of matching tasks.
        """
        results: list[Task] = []
        for task in self._tasks.values():
            if not include_deleted and task.is_deleted:
                continue
            if owner_id and task.owner_id != owner_id and task.assignee_id != owner_id:
                continue
            if status and task.status != status:
                continue
            if priority and task.priority != priority:
                continue
            results.append(task)
        return results

    def save_history(self, history: TaskHistory) -> None:
        """Append history entry for a task.

        Args:
            history: History entry.
        """
        if history.task_id not in self._history:
            self._history[history.task_id] = []
        self._history[history.task_id].append(history)

    def get_history(self, task_id: str) -> list[TaskHistory]:
        """Retrieve task change records in insertion order.

        Args:
            task_id: Task identifier.

        Returns:
            List of TaskHistory records.
        """
        return list(self._history.get(task_id, []))

    def save_notification(self, notification: Notification) -> None:
        """Save user notification.

        Args:
            notification: Notification entity.
        """
        if notification.user_id not in self._notifications:
            self._notifications[notification.user_id] = []
        self._notifications[notification.user_id].append(notification)

    def list_notifications(self, user_id: str) -> list[Notification]:
        """List notifications for a user.

        Args:
            user_id: User identifier.

        Returns:
            List of user notifications.
        """
        return list(self._notifications.get(user_id, []))

    def mark_notification_read(self, notification_id: str) -> Notification | None:
        """Mark notification as read across user collections.

        Args:
            notification_id: Notification identifier.

        Returns:
            Updated notification or None.
        """
        for user_id, notifs in self._notifications.items():
            for i, n in enumerate(notifs):
                if n.id == notification_id:
                    updated = Notification(
                        id=n.id,
                        user_id=n.user_id,
                        task_id=n.task_id,
                        title=n.title,
                        message=n.message,
                        is_read=True,
                        created_at=n.created_at,
                    )
                    self._notifications[user_id][i] = updated
                    return updated
        return None

    def save_user(self, user: User) -> None:
        """Store or update user profile.

        Args:
            user: User entity.
        """
        self._users[user.id] = user

    def get_user(self, user_id: str) -> User | None:
        """Retrieve user by identifier.

        Args:
            user_id: User identifier.

        Returns:
            User entity or None.
        """
        return self._users.get(user_id)
