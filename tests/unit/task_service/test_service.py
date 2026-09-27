"""Unit tests for task domain service."""

import pytest
from modules.task_service.adapters.memory_task_repo import InMemoryTaskRepository
from modules.task_service.domain.models import User
from modules.task_service.domain.service import TaskService


def test_create_and_get_task():
    """Verify task creation and retrieval rules."""
    repo = InMemoryTaskRepository()
    svc = TaskService(repo)

    task = svc.create_task(title="Build Maestro", owner_id="npintaux", notes="Priority project")
    assert task.title == "Build Maestro"
    assert task.owner_id == "npintaux"

    fetched = svc.get_task(task.id, actor_id="npintaux")
    assert fetched.id == task.id

    # Non-existent task raises KeyError
    with pytest.raises(KeyError):
        svc.get_task("nonexistent", actor_id="npintaux")

    # Unauthorized access raises PermissionError
    with pytest.raises(PermissionError):
        svc.get_task(task.id, actor_id="stranger", actor_role="employee")

    # Auditor, Lead, Admin can view
    for role in ("auditor", "lead", "admin"):
        assert svc.get_task(task.id, actor_id="stranger", actor_role=role).id == task.id


def test_create_task_empty_title():
    """Verify ValueError on empty title."""
    repo = InMemoryTaskRepository()
    svc = TaskService(repo)
    with pytest.raises(ValueError, match="Task title is required"):
        svc.create_task("", "owner")


def test_update_task():
    """Verify updating task properties and permission checks."""
    repo = InMemoryTaskRepository()
    svc = TaskService(repo)
    task = svc.create_task("Initial Title", "owner")

    updated = svc.update_task(
        task.id,
        actor_id="owner",
        title="Updated Title",
        notes="New Notes",
        priority="urgent",
        due_date="2026-12-31",
    )
    assert updated.title == "Updated Title"
    assert updated.notes == "New Notes"
    assert updated.priority == "urgent"
    assert updated.due_date == "2026-12-31"

    # Unauthorized edit raises PermissionError
    with pytest.raises(PermissionError):
        svc.update_task(task.id, actor_id="stranger", title="Hacked")


def test_transition_status():
    """Verify state transitions via service."""
    repo = InMemoryTaskRepository()
    svc = TaskService(repo)
    task = svc.create_task("Task 1", "owner")

    t1 = svc.transition_status(task.id, "in_progress", actor_id="owner")
    assert t1.status == "in_progress"

    # Unauthorized transition
    with pytest.raises(PermissionError):
        svc.transition_status(task.id, "done", actor_id="other")


def test_delete_and_restore():
    """Verify soft deletion and restoration lifecycle."""
    repo = InMemoryTaskRepository()
    svc = TaskService(repo)
    task = svc.create_task("To Delete", "owner")

    # Delete
    deleted = svc.delete_task(task.id, actor_id="owner")
    assert deleted.is_deleted is True
    assert deleted.deleted_at is not None

    # Already deleted cannot be re-restored when not deleted
    restored = svc.restore_task(task.id, actor_id="owner")
    assert restored.is_deleted is False

    with pytest.raises(ValueError, match="is not deleted"):
        svc.restore_task(task.id, actor_id="owner")

    # Non-existent restore
    with pytest.raises(KeyError):
        svc.restore_task("missing", actor_id="owner")

    # Unauthorized delete
    task2 = svc.create_task("Task 2", "owner")
    with pytest.raises(PermissionError):
        svc.delete_task(task2.id, actor_id="stranger")

    # Unauthorized restore
    svc.delete_task(task2.id, actor_id="owner")
    with pytest.raises(PermissionError):
        svc.restore_task(task2.id, actor_id="stranger")


def test_share_task():
    """Verify task sharing and notification dispatch."""
    repo = InMemoryTaskRepository()
    svc = TaskService(repo)
    task = svc.create_task("Shared Task", "owner")

    svc.share_task(task.id, actor_id="owner", target_user_id="collaborator", permission="edit")
    shared_task = svc.get_task(task.id, actor_id="collaborator")
    assert len(shared_task.shares) == 1

    # Check notification sent to collaborator
    notifs = svc.list_notifications("collaborator")
    assert len(notifs) == 1
    assert "Shared Task" in notifs[0].message

    # Unauthorized share
    with pytest.raises(PermissionError):
        svc.share_task(task.id, actor_id="stranger", target_user_id="other", permission="view")


def test_reassign_task():
    """Verify team lead reassignment and notification."""
    repo = InMemoryTaskRepository()
    svc = TaskService(repo)
    task = svc.create_task("Handover Task", "dev1")

    # Employee cannot reassign
    with pytest.raises(PermissionError, match="Only team leads"):
        svc.reassign_task(task.id, "dev2", actor_id="dev1", actor_role="employee")

    # Team lead reassigns
    reassigned = svc.reassign_task(
        task.id, "dev2", actor_id="lead_user", actor_role="lead", reason="Follow the sun handoff"
    )
    assert reassigned.owner_id == "dev2"
    assert reassigned.assignee_id == "dev2"

    notifs = svc.list_notifications("dev2")
    assert len(notifs) == 1

    # Reassign missing task
    with pytest.raises(KeyError):
        svc.reassign_task("missing", "dev2", actor_id="lead", actor_role="lead")


def test_orphaned_tasks_and_user_status():
    """Verify identifying orphaned tasks from deactivated accounts."""
    repo = InMemoryTaskRepository()
    svc = TaskService(repo)

    # Set up user
    user = svc.set_user_status("emp1", is_active=True, actor_role="admin")
    assert user.is_active is True

    # Non-admin cannot set user status
    with pytest.raises(PermissionError):
        svc.set_user_status("emp1", is_active=False, actor_role="employee")

    # Create task
    task = svc.create_task("Task of emp1", owner_id="emp1")

    # Deactivate user
    svc.set_user_status("emp1", is_active=False, actor_role="admin")

    # List orphaned tasks
    orphans = svc.list_orphaned_tasks(actor_role="lead")
    assert len(orphans) == 1
    assert orphans[0].id == task.id

    # Non-lead cannot view orphaned tasks
    with pytest.raises(PermissionError):
        svc.list_orphaned_tasks(actor_role="employee")


def test_history_and_notification_read():
    """Verify change history tracking and marking notifications as read."""
    repo = InMemoryTaskRepository()
    svc = TaskService(repo)
    task = svc.create_task("History Task", "owner")
    svc.update_task(task.id, "owner", title="Updated")

    history = svc.get_history(task.id, "owner")
    assert len(history) == 2

    svc.share_task(task.id, "owner", "u2", "view")
    notifs = svc.list_notifications("u2")
    assert len(notifs) == 1

    marked = svc.mark_notification_read(notifs[0].id)
    assert marked is not None
    assert marked.is_read is True


def test_permission_branches_and_roles():
    """Verify detailed permission checks for view-only vs edit vs admin."""
    repo = InMemoryTaskRepository()
    svc = TaskService(repo)
    task = svc.create_task("Protected Task", "owner_user")

    # Share with viewer (view-only)
    svc.share_task(task.id, "owner_user", "viewer_user", "view")

    # Viewer cannot edit or transition
    with pytest.raises(PermissionError):
        svc.update_task(task.id, actor_id="viewer_user", title="Changed")

    with pytest.raises(PermissionError):
        svc.transition_status(task.id, "in_progress", actor_id="viewer_user")

    # Viewer cannot delete or share
    with pytest.raises(PermissionError):
        svc.delete_task(task.id, actor_id="viewer_user")

    with pytest.raises(PermissionError):
        svc.share_task(task.id, actor_id="viewer_user", target_user_id="other", permission="view")

    # Admin and Lead can edit, share, and delete even if not owner
    svc.update_task(task.id, actor_id="admin_user", actor_role="admin", title="Admin Edit")
    svc.share_task(
        task.id,
        actor_id="lead_user",
        target_user_id="collaborator",
        permission="edit",
        actor_role="lead",
    )
    # Collaborator with edit share CAN edit and transition
    svc.update_task(task.id, actor_id="collaborator", notes="Collaborator note")
    svc.transition_status(task.id, "in_progress", actor_id="collaborator")

    # Admin can delete
    deleted = svc.delete_task(task.id, actor_id="admin_user", actor_role="admin")
    assert deleted.is_deleted is True
