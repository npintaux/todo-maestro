"""Abstract persistence port for task entities, history, and notifications."""

from __future__ import annotations

from abc import ABC, abstractmethod

from modules.task_service.domain.models import Notification, Task, TaskHistory, User


class TaskRepository(ABC):
    """Abstract persistence interface for the task domain."""

    @abstractmethod
    def save_task(self, task: Task) -> None:
        """Persist or update a task entity.

        Args:
            task: Task to store.
        """
        raise NotImplementedError

    @abstractmethod
    def get_task(self, task_id: str) -> Task | None:
        """Retrieve a task by ID.

        Args:
            task_id: Task identifier.

        Returns:
            Matching Task or None.
        """
        raise NotImplementedError

    @abstractmethod
    def list_tasks(
        self,
        owner_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        include_deleted: bool = False,
    ) -> list[Task]:
        """List tasks according to filter criteria.

        Args:
            owner_id: Optional owner filter.
            status: Optional status filter.
            priority: Optional priority filter.
            include_deleted: Whether to include soft-deleted tasks.

        Returns:
            List of matching tasks.
        """
        raise NotImplementedError

    @abstractmethod
    def save_history(self, history: TaskHistory) -> None:
        """Append a history entry to the task's audit trail.

        Args:
            history: History record to append.
        """
        raise NotImplementedError

    @abstractmethod
    def get_history(self, task_id: str) -> list[TaskHistory]:
        """Retrieve chronological history for a task.

        Args:
            task_id: Task identifier.

        Returns:
            List of history entries in chronological order.
        """
        raise NotImplementedError

    @abstractmethod
    def save_notification(self, notification: Notification) -> None:
        """Store an in-app notification.

        Args:
            notification: Notification entity.
        """
        raise NotImplementedError

    @abstractmethod
    def list_notifications(self, user_id: str) -> list[Notification]:
        """Retrieve notifications for a user.

        Args:
            user_id: Target user identifier.

        Returns:
            List of user notifications.
        """
        raise NotImplementedError

    @abstractmethod
    def mark_notification_read(self, notification_id: str) -> Notification | None:
        """Mark notification as read.

        Args:
            notification_id: Notification identifier.

        Returns:
            Updated notification or None.
        """
        raise NotImplementedError

    @abstractmethod
    def save_user(self, user: User) -> None:
        """Store or update user profile.

        Args:
            user: User entity.
        """
        raise NotImplementedError

    @abstractmethod
    def get_user(self, user_id: str) -> User | None:
        """Retrieve user by identifier.

        Args:
            user_id: User identifier.

        Returns:
            User entity or None.
        """
        raise NotImplementedError
