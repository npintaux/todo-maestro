"""Finite state machine governing task lifecycle status transitions."""

from __future__ import annotations

from datetime import UTC, datetime

from modules.task_service.domain.models import Task, TaskHistory


class TaskStateMachine:
    """Encapsulates transition rules, invariants, and guard conditions for tasks."""

    ALLOWED_TRANSITIONS: dict[str, set[str]] = {
        "open": {"in_progress"},
        "in_progress": {"done", "open"},
        "done": {"open"},
    }

    def can_transition(self, task: Task, new_status: str, actor_id: str) -> bool:
        """Evaluate if the task can legally transition to the requested status.

        Args:
            task: The target task entity.
            new_status: Desired next status.
            actor_id: Principal requesting transition.

        Returns:
            True if transition is allowed, False otherwise.
        """
        if task.is_deleted:
            return False
        if not self._is_authorized_actor(task, actor_id):
            return False
        allowed_targets = self.ALLOWED_TRANSITIONS.get(task.status, set())
        return new_status in allowed_targets

    def transition(
        self,
        task: Task,
        new_status: str,
        actor_id: str,
        reason: str = "",
    ) -> TaskHistory:
        """Execute state transition on task and return corresponding history record.

        Args:
            task: Task to transition.
            new_status: Target status value.
            actor_id: Initiating user.
            reason: Optional explanation.

        Returns:
            Recorded TaskHistory entry.

        Raises:
            ValueError: If transition violates FSM invariants or authorization.
        """
        if not self.can_transition(task, new_status, actor_id):
            raise ValueError(
                f"Cannot transition task {task.id} from '{task.status}' to '{new_status}' "
                f"by actor '{actor_id}'."
            )

        before_status = task.status
        task.status = new_status
        task.updated_at = datetime.now(UTC).isoformat()

        return TaskHistory(
            task_id=task.id,
            actor_id=actor_id,
            action="status_transition",
            before={"status": before_status},
            after={"status": new_status, "reason": reason},
        )

    def _is_authorized_actor(self, task: Task, actor_id: str) -> bool:
        """Check if actor is owner, assignee, or has edit share on task."""
        if task.owner_id == actor_id or task.assignee_id == actor_id:
            return True
        for share in task.shares:
            if share.user_id == actor_id and share.permission == "edit":
                return True
        return False
