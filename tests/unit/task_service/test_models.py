"""Unit tests for task_service domain models."""

from modules.task_service.domain.models import (
    Notification,
    Task,
    TaskHistory,
    TaskShare,
    User,
)


def test_user_model():
    """Verify User model attributes and serialization."""
    user = User(id="u1", email="u1@test.com", role="employee", is_active=True)
    d = user.to_dict()
    assert d["id"] == "u1"
    assert d["email"] == "u1@test.com"
    assert d["role"] == "employee"
    assert d["is_active"] is True


def test_task_share_model():
    """Verify TaskShare model attributes and serialization."""
    share = TaskShare(user_id="u2", permission="edit")
    d = share.to_dict()
    assert d["user_id"] == "u2"
    assert d["permission"] == "edit"


def test_task_history_model():
    """Verify TaskHistory model attributes and serialization."""
    history = TaskHistory(
        task_id="t1",
        actor_id="u1",
        action="update",
        before={"title": "old"},
        after={"title": "new"},
    )
    d = history.to_dict()
    assert d["task_id"] == "t1"
    assert d["actor_id"] == "u1"
    assert d["action"] == "update"
    assert d["before"]["title"] == "old"
    assert d["after"]["title"] == "new"
    assert "timestamp" in d
    assert "id" in d


def test_notification_model():
    """Verify Notification model attributes and serialization."""
    notif = Notification(
        user_id="u1",
        title="Alert",
        message="Message body",
        task_id="t1",
    )
    d = notif.to_dict()
    assert d["user_id"] == "u1"
    assert d["title"] == "Alert"
    assert d["message"] == "Message body"
    assert d["task_id"] == "t1"
    assert d["is_read"] is False
    assert "created_at" in d


def test_task_model():
    """Verify Task model attributes and serialization."""
    task = Task(
        title="Implement TaskFlow",
        owner_id="u1",
        notes="Important notes",
        priority="high",
        due_date="2026-10-01",
        shares=[TaskShare(user_id="u2", permission="view")],
    )
    d = task.to_dict()
    assert d["title"] == "Implement TaskFlow"
    assert d["owner_id"] == "u1"
    assert d["assignee_id"] == "u1"
    assert d["status"] == "open"
    assert d["priority"] == "high"
    assert d["is_deleted"] is False
    assert len(d["shares"]) == 1
    assert d["shares"][0]["user_id"] == "u2"
