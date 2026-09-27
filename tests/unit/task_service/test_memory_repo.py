"""Unit tests for in-memory task repository adapter."""

from modules.task_service.adapters.memory_task_repo import InMemoryTaskRepository
from modules.task_service.domain.models import Task, User


def test_repository_task_filters():
    """Verify task filtering across status, priority, owner, and soft deletion."""
    repo = InMemoryTaskRepository()
    t1 = Task(title="T1", owner_id="u1", status="open", priority="low")
    t2 = Task(title="T2", owner_id="u1", status="done", priority="high")
    t3 = Task(title="T3", owner_id="u2", status="open", priority="high", is_deleted=True)

    repo.save_task(t1)
    repo.save_task(t2)
    repo.save_task(t3)

    assert len(repo.list_tasks(include_deleted=False)) == 2
    assert len(repo.list_tasks(include_deleted=True)) == 3
    assert len(repo.list_tasks(status="open")) == 1
    assert len(repo.list_tasks(priority="high")) == 1
    assert len(repo.list_tasks(owner_id="u1")) == 2
    assert len(repo.list_tasks(owner_id="unknown_owner")) == 0

    # Non-existent notification
    assert repo.mark_notification_read("nonexistent") is None


def test_repository_user_storage():
    """Verify storing and retrieving user records."""
    repo = InMemoryTaskRepository()
    user = User(id="u1", email="u1@example.com")
    repo.save_user(user)

    assert repo.get_user("u1") == user
    assert repo.get_user("missing") is None
