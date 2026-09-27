"""Unit tests for task state machine."""

import pytest
from modules.task_service.domain.models import Task, TaskShare
from modules.task_service.domain.state_machine import TaskStateMachine


def test_state_machine_legal_transitions():
    """Verify standard legal lifecycle transitions."""
    fsm = TaskStateMachine()
    task = Task(title="Test", owner_id="u1")

    # open -> in_progress
    assert fsm.can_transition(task, "in_progress", "u1")
    history1 = fsm.transition(task, "in_progress", "u1", reason="Starting work")
    assert task.status == "in_progress"
    assert history1.before["status"] == "open"
    assert history1.after["status"] == "in_progress"

    # in_progress -> done
    assert fsm.can_transition(task, "done", "u1")
    history2 = fsm.transition(task, "done", "u1", reason="Completed")
    assert task.status == "done"
    assert history2.after["status"] == "done"

    # done -> open (reopen)
    assert fsm.can_transition(task, "open", "u1")
    history3 = fsm.transition(task, "open", "u1", reason="Reopening")
    assert task.status == "open"

    # in_progress -> open
    fsm.transition(task, "in_progress", "u1")
    assert fsm.can_transition(task, "open", "u1")
    fsm.transition(task, "open", "u1")
    assert task.status == "open"


def test_state_machine_illegal_transition():
    """Verify illegal transitions are rejected."""
    fsm = TaskStateMachine()
    task = Task(title="Test", owner_id="u1")

    # open -> done without in_progress
    assert not fsm.can_transition(task, "done", "u1")
    with pytest.raises(ValueError, match="Cannot transition task"):
        fsm.transition(task, "done", "u1")


def test_state_machine_deleted_task_cannot_transition():
    """Verify deleted tasks cannot transition."""
    fsm = TaskStateMachine()
    task = Task(title="Test", owner_id="u1", is_deleted=True)
    assert not fsm.can_transition(task, "in_progress", "u1")


def test_state_machine_unauthorized_actor():
    """Verify actor without permissions cannot transition."""
    fsm = TaskStateMachine()
    task = Task(title="Test", owner_id="u1")
    assert not fsm.can_transition(task, "in_progress", "stranger")

    # Share with edit permission
    task.shares.append(TaskShare(user_id="collaborator", permission="edit"))
    assert fsm.can_transition(task, "in_progress", "collaborator")

    # Share with view-only permission
    task.shares.append(TaskShare(user_id="viewer", permission="view"))
    assert not fsm.can_transition(task, "in_progress", "viewer")
