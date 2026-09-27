"""Domain service coordinating task operations, follow-the-sun workflows, and notifications."""

from __future__ import annotations

from datetime import UTC, datetime

from modules.task_service.domain.models import (
    Notification,
    Task,
    TaskHistory,
    TaskShare,
    User,
)
from modules.task_service.domain.repository import TaskRepository
from modules.task_service.domain.state_machine import TaskStateMachine


class TaskService:
    """Business coordinator for tasks, sharing, reassignment, and notifications."""

    def __init__(
        self,
        repository: TaskRepository,
        state_machine: TaskStateMachine | None = None,
    ) -> None:
        """Initialize task service with repository and state machine.

        Args:
            repository: Persistence adapter.
            state_machine: Lifecycle state machine.
        """
        self._repo = repository
        self._fsm = state_machine or TaskStateMachine()

    def create_task(
        self,
        title: str,
        owner_id: str,
        notes: str = "",
        priority: str = "medium",
        due_date: str | None = None,
    ) -> Task:
        """Create a new task in open status.

        Args:
            title: Task summary title.
            owner_id: Creator and default owner.
            notes: Detailed description or notes.
            priority: Urgency tier (low, medium, high, urgent).
            due_date: Optional deadline ISO timestamp.

        Returns:
            Created Task entity.
        """
        if not title:
            raise ValueError("Task title is required.")

        task = Task(
            title=title,
            owner_id=owner_id,
            notes=notes,
            priority=priority,
            due_date=due_date,
        )
        self._repo.save_task(task)

        history = TaskHistory(
            task_id=task.id,
            actor_id=owner_id,
            action="task_created",
            before={},
            after=task.to_dict(),
        )
        self._repo.save_history(history)
        return task

    def get_task(self, task_id: str, actor_id: str, actor_role: str = "employee") -> Task:
        """Retrieve task details if actor is authorized.

        Args:
            task_id: Task identifier.
            actor_id: Requesting user.
            actor_role: Requesting user role.

        Returns:
            Task entity.

        Raises:
            KeyError: If task does not exist.
            PermissionError: If actor lacks view access.
        """
        task = self._repo.get_task(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found.")

        if not self._can_view(task, actor_id, actor_role):
            raise PermissionError(f"User {actor_id} is not authorized to view task {task_id}.")

        return task

    def list_tasks(
        self,
        actor_id: str,
        actor_role: str = "employee",
        status: str | None = None,
        priority: str | None = None,
        owner_id: str | None = None,
    ) -> list[Task]:
        """List tasks visible to the actor with optional filters.

        Args:
            actor_id: Requesting user.
            actor_role: Requesting user role.
            status: Optional status filter.
            priority: Optional priority filter.
            owner_id: Optional owner filter.

        Returns:
            List of matching tasks.
        """
        tasks = self._repo.list_tasks(owner_id=owner_id, status=status, priority=priority)
        return [t for t in tasks if self._can_view(t, actor_id, actor_role)]

    def update_task(
        self,
        task_id: str,
        actor_id: str,
        actor_role: str = "employee",
        title: str | None = None,
        notes: str | None = None,
        priority: str | None = None,
        due_date: str | None = None,
    ) -> Task:
        """Update editable attributes of a task.

        Args:
            task_id: Task identifier.
            actor_id: Modifying user.
            actor_role: User role.
            title: Optional updated title.
            notes: Optional updated notes.
            priority: Optional updated priority.
            due_date: Optional updated deadline.

        Returns:
            Updated task entity.
        """
        task = self.get_task(task_id, actor_id, actor_role)
        if not self._can_edit(task, actor_id, actor_role):
            raise PermissionError(f"User {actor_id} is not authorized to edit task {task_id}.")

        before = task.to_dict()
        if title is not None:
            task.title = title
        if notes is not None:
            task.notes = notes
        if priority is not None:
            task.priority = priority
        if due_date is not None:
            task.due_date = due_date
        task.updated_at = datetime.now(UTC).isoformat()

        self._repo.save_task(task)
        history = TaskHistory(
            task_id=task.id,
            actor_id=actor_id,
            action="task_updated",
            before=before,
            after=task.to_dict(),
        )
        self._repo.save_history(history)
        return task

    def transition_status(
        self,
        task_id: str,
        new_status: str,
        actor_id: str,
        actor_role: str = "employee",
        reason: str = "",
    ) -> Task:
        """Transition task status using the state machine.

        Args:
            task_id: Task identifier.
            new_status: Target status.
            actor_id: Actor requesting transition.
            actor_role: Actor role.
            reason: Optional justification.

        Returns:
            Updated task entity.
        """
        task = self.get_task(task_id, actor_id, actor_role)
        if not self._can_edit(task, actor_id, actor_role):
            raise PermissionError(
                f"User {actor_id} is not authorized to transition task {task_id}."
            )

        history_entry = self._fsm.transition(task, new_status, actor_id, reason)
        self._repo.save_task(task)
        self._repo.save_history(history_entry)
        return task

    def delete_task(self, task_id: str, actor_id: str, actor_role: str = "employee") -> Task:
        """Soft-delete a task, retaining its history.

        Args:
            task_id: Task identifier.
            actor_id: Actor requesting deletion.
            actor_role: Actor role.

        Returns:
            Soft-deleted task entity.
        """
        task = self.get_task(task_id, actor_id, actor_role)
        if task.owner_id != actor_id and actor_role not in ("admin", "lead"):
            raise PermissionError(f"Only the owner can delete task {task_id}.")

        task.is_deleted = True
        task.deleted_at = datetime.now(UTC).isoformat()
        self._repo.save_task(task)

        history = TaskHistory(
            task_id=task.id,
            actor_id=actor_id,
            action="task_deleted",
            before={"is_deleted": False},
            after={"is_deleted": True, "deleted_at": task.deleted_at},
        )
        self._repo.save_history(history)
        return task

    def restore_task(self, task_id: str, actor_id: str, actor_role: str = "employee") -> Task:
        """Restore a soft-deleted task.

        Args:
            task_id: Task identifier.
            actor_id: Actor requesting restoration.
            actor_role: Actor role.

        Returns:
            Restored task entity.
        """
        task = self._repo.get_task(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found.")
        if not task.is_deleted:
            raise ValueError(f"Task {task_id} is not deleted.")
        if task.owner_id != actor_id and actor_role not in ("admin", "lead"):
            raise PermissionError(f"Only the owner can restore task {task_id}.")

        task.is_deleted = False
        task.deleted_at = None
        task.updated_at = datetime.now(UTC).isoformat()
        self._repo.save_task(task)

        history = TaskHistory(
            task_id=task.id,
            actor_id=actor_id,
            action="task_restored",
            before={"is_deleted": True},
            after={"is_deleted": False},
        )
        self._repo.save_history(history)
        return task

    def share_task(
        self,
        task_id: str,
        actor_id: str,
        target_user_id: str,
        permission: str,
        actor_role: str = "employee",
    ) -> Task:
        """Share access to a task with another user.

        Args:
            task_id: Task identifier.
            actor_id: Current owner.
            target_user_id: Recipient of share permission.
            permission: "view" or "edit".
            actor_role: Current user role.

        Returns:
            Updated task entity.
        """
        task = self.get_task(task_id, actor_id, actor_role)
        if task.owner_id != actor_id and actor_role not in ("admin", "lead"):
            raise PermissionError(f"Only the owner can share task {task_id}.")

        # Replace or add share
        updated_shares = [s for s in task.shares if s.user_id != target_user_id]
        updated_shares.append(TaskShare(user_id=target_user_id, permission=permission))
        task.shares = updated_shares
        task.updated_at = datetime.now(UTC).isoformat()
        self._repo.save_task(task)

        history = TaskHistory(
            task_id=task.id,
            actor_id=actor_id,
            action="task_shared",
            before={},
            after={"target_user_id": target_user_id, "permission": permission},
        )
        self._repo.save_history(history)

        # Notify recipient
        notification = Notification(
            user_id=target_user_id,
            task_id=task.id,
            title="Task Shared With You",
            message=f"User {actor_id} shared '{task.title}' with {permission} access.",
        )
        self._repo.save_notification(notification)
        return task

    def reassign_task(
        self,
        task_id: str,
        new_owner_id: str,
        actor_id: str,
        actor_role: str,
        reason: str = "",
    ) -> Task:
        """Reassign task ownership to a new employee.

        Args:
            task_id: Task identifier.
            new_owner_id: Target assignee.
            actor_id: Reassigning user.
            actor_role: Role of actor (must be lead or admin).
            reason: Reassignment justification.

        Returns:
            Updated task entity.
        """
        if actor_role not in ("lead", "admin"):
            raise PermissionError("Only team leads and administrators can reassign tasks.")

        task = self._repo.get_task(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found.")

        old_owner = task.owner_id
        task.owner_id = new_owner_id
        task.assignee_id = new_owner_id
        task.updated_at = datetime.now(UTC).isoformat()
        self._repo.save_task(task)

        history = TaskHistory(
            task_id=task.id,
            actor_id=actor_id,
            action="task_reassigned",
            before={"owner_id": old_owner},
            after={"owner_id": new_owner_id, "reason": reason},
        )
        self._repo.save_history(history)

        notification = Notification(
            user_id=new_owner_id,
            task_id=task.id,
            title="Task Assigned to You",
            message=f"You have been assigned '{task.title}' by {actor_id}.",
        )
        self._repo.save_notification(notification)
        return task

    def list_orphaned_tasks(self, actor_role: str) -> list[Task]:
        """List active tasks owned by deactivated users.

        Args:
            actor_role: Role of requesting user (lead or admin).

        Returns:
            List of orphaned tasks.
        """
        if actor_role not in ("lead", "admin"):
            raise PermissionError("Only team leads and administrators can view orphaned tasks.")

        all_tasks = self._repo.list_tasks(include_deleted=False)
        orphaned: list[Task] = []
        for t in all_tasks:
            if t.status in ("open", "in_progress"):
                user = self._repo.get_user(t.owner_id)
                if user is not None and not user.is_active:
                    orphaned.append(t)
        return orphaned

    def set_user_status(self, user_id: str, is_active: bool, actor_role: str) -> User:
        """Update active status of a user account.

        Args:
            user_id: Target user.
            is_active: Active state flag.
            actor_role: Role of actor (admin required).

        Returns:
            Updated user entity.
        """
        if actor_role != "admin":
            raise PermissionError("Only administrators can update user status.")

        user = self._repo.get_user(user_id)
        if user is None:
            user = User(id=user_id, email=f"{user_id}@example.com", is_active=is_active)
        else:
            user = User(id=user.id, email=user.email, role=user.role, is_active=is_active)
        self._repo.save_user(user)
        return user

    def get_history(
        self,
        task_id: str,
        actor_id: str,
        actor_role: str = "employee",
    ) -> list[TaskHistory]:
        """Retrieve task change audit trail.

        Args:
            task_id: Task identifier.
            actor_id: Requesting user.
            actor_role: User role.

        Returns:
            List of TaskHistory records.
        """
        self.get_task(task_id, actor_id, actor_role)
        return self._repo.get_history(task_id)

    def list_notifications(self, user_id: str) -> list[Notification]:
        """List all notifications for a user.

        Args:
            user_id: Target user.

        Returns:
            List of notifications.
        """
        return self._repo.list_notifications(user_id)

    def mark_notification_read(self, notification_id: str) -> Notification | None:
        """Mark notification as read.

        Args:
            notification_id: Notification identifier.

        Returns:
            Updated notification or None.
        """
        return self._repo.mark_notification_read(notification_id)

    def _can_view(self, task: Task, actor_id: str, actor_role: str) -> bool:
        """Check if actor is permitted to view task."""
        if actor_role in ("admin", "lead", "auditor"):
            return True
        if task.owner_id == actor_id or task.assignee_id == actor_id:
            return True
        for s in task.shares:
            if s.user_id == actor_id:
                return True
        return False

    def _can_edit(self, task: Task, actor_id: str, actor_role: str) -> bool:
        """Check if actor is permitted to edit task."""
        if actor_role in ("admin", "lead"):
            return True
        if task.owner_id == actor_id or task.assignee_id == actor_id:
            return True
        for s in task.shares:
            if s.user_id == actor_id and s.permission == "edit":
                return True
        return False
