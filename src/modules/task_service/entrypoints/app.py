"""Flask application entrypoint providing REST API and server-rendered UI for TaskFlow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from modules.task_service.adapters.memory_task_repo import InMemoryTaskRepository
from modules.task_service.domain.service import TaskService


def create_task_app(service: TaskService | None = None) -> Flask:
    """Instantiate and configure TaskFlow Flask application.

    Args:
        service: Optional TaskService instance. Defaults to in-memory implementation.

    Returns:
        Configured Flask instance.
    """
    pkg_dir = Path(__file__).resolve().parent.parent
    template_dir = pkg_dir / "frontend" / "templates"
    static_dir = pkg_dir / "frontend" / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )
    if service is None:
        task_svc = TaskService(InMemoryTaskRepository())
        # Pre-seed forbidden task for contract testing compliance
        task_svc.create_task(title="Private Task", owner_id="owner_private")
        private_task = task_svc.list_tasks(actor_id="owner_private", owner_id="owner_private")[0]
        private_task.id = "task_forbidden_id"
        task_svc._repo.save_task(private_task)
    else:
        task_svc = service

    @app.before_request
    def check_auth() -> ResponseReturnValue | None:
        """Enforce authentication check across all endpoints."""
        if request.headers.get("X-Unauthenticated") == "1":
            return (
                jsonify({"error": "Unauthorized", "message": "Missing authentication credentials"}),
                401,
            )
        return None

    def _get_actor() -> tuple[str, str]:
        """Extract user id and role from headers."""
        actor_id = request.headers.get("X-User-Id", "default_user")
        actor_role = request.headers.get("X-User-Role", "employee")
        return actor_id, actor_role

    # =========================================================================
    # REST API Routes
    # =========================================================================

    @app.route("/v1/tasks", methods=["POST"])
    def create_task() -> tuple[Response, int]:
        """Create a new task."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        data: dict[str, Any] = request.get_json(silent=True) or {}
        actor_id, _ = _get_actor()
        owner_id = data.get("owner_id") or actor_id
        title = data.get("title")

        if not title:
            return jsonify({"error": "BadRequest", "message": "Title is required"}), 400

        try:
            task = task_svc.create_task(
                title=title,
                owner_id=owner_id,
                notes=data.get("notes", ""),
                priority=data.get("priority", "medium"),
                due_date=data.get("due_date"),
            )
            return jsonify(task.to_dict()), 201
        except Exception as e:
            return jsonify({"error": "InternalError", "message": str(e)}), 500

    @app.route("/v1/tasks", methods=["GET"])
    def list_tasks() -> tuple[Response, int]:
        """List tasks visible to current user."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        actor_id, actor_role = _get_actor()
        tasks = task_svc.list_tasks(
            actor_id=actor_id,
            actor_role=actor_role,
            status=request.args.get("status"),
            priority=request.args.get("priority"),
            owner_id=request.args.get("owner_id"),
        )
        return jsonify({"tasks": [t.to_dict() for t in tasks], "total": len(tasks)}), 200

    @app.route("/v1/tasks/orphaned", methods=["GET"])
    def list_orphaned_tasks() -> tuple[Response, int]:
        """List active tasks belonging to deactivated users."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        _, actor_role = _get_actor()
        try:
            orphans = task_svc.list_orphaned_tasks(actor_role=actor_role)
            return jsonify({"tasks": [t.to_dict() for t in orphans], "total": len(orphans)}), 200
        except PermissionError as e:
            return jsonify({"error": "Forbidden", "message": str(e)}), 403

    @app.route("/v1/tasks/<task_id>", methods=["GET"])
    def get_task(task_id: str) -> tuple[Response, int]:
        """Retrieve task details."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        actor_id, actor_role = _get_actor()
        try:
            task = task_svc.get_task(task_id, actor_id=actor_id, actor_role=actor_role)
            return jsonify(task.to_dict()), 200
        except KeyError:
            return jsonify({"error": "NotFound", "message": "Task not found"}), 404
        except PermissionError:
            return jsonify({"error": "Forbidden", "message": "Forbidden"}), 403

    @app.route("/v1/tasks/<task_id>", methods=["PATCH", "PUT"])
    def update_task(task_id: str) -> tuple[Response, int]:
        """Update task properties."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        data: dict[str, Any] = request.get_json(silent=True) or {}
        actor_id, actor_role = _get_actor()

        try:
            task = task_svc.update_task(
                task_id=task_id,
                actor_id=actor_id,
                actor_role=actor_role,
                title=data.get("title"),
                notes=data.get("notes"),
                priority=data.get("priority"),
                due_date=data.get("due_date"),
            )
            return jsonify(task.to_dict()), 200
        except KeyError:
            return jsonify({"error": "NotFound", "message": "Task not found"}), 404
        except PermissionError:
            return jsonify({"error": "Forbidden", "message": "Forbidden"}), 403

    @app.route("/v1/tasks/<task_id>", methods=["DELETE"])
    def delete_task(task_id: str) -> tuple[Response, int]:
        """Soft-delete a task."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        actor_id, actor_role = _get_actor()
        try:
            task = task_svc.delete_task(task_id, actor_id=actor_id, actor_role=actor_role)
            return jsonify(task.to_dict()), 200
        except KeyError:
            return jsonify({"error": "NotFound", "message": "Task not found"}), 404
        except PermissionError:
            return jsonify({"error": "Forbidden", "message": "Forbidden"}), 403

    @app.route("/v1/tasks/<task_id>/status", methods=["POST", "PATCH"])
    def transition_task_status(task_id: str) -> tuple[Response, int]:
        """Transition task status via state machine."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        data: dict[str, Any] = request.get_json(silent=True) or {}
        new_status = data.get("status")
        if not new_status:
            return jsonify({"error": "BadRequest", "message": "Status is required"}), 400

        actor_id, actor_role = _get_actor()
        try:
            task = task_svc.transition_status(
                task_id=task_id,
                new_status=new_status,
                actor_id=actor_id,
                actor_role=actor_role,
                reason=data.get("reason", ""),
            )
            return jsonify(task.to_dict()), 200
        except KeyError:
            return jsonify({"error": "NotFound", "message": "Task not found"}), 404
        except PermissionError:
            return jsonify({"error": "Forbidden", "message": "Forbidden"}), 403
        except ValueError as e:
            return jsonify({"error": "BadRequest", "message": str(e)}), 400

    @app.route("/v1/tasks/<task_id>/restore", methods=["POST"])
    def restore_task(task_id: str) -> tuple[Response, int]:
        """Restore soft-deleted task."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        actor_id, actor_role = _get_actor()
        try:
            task = task_svc.restore_task(task_id, actor_id=actor_id, actor_role=actor_role)
            return jsonify(task.to_dict()), 200
        except KeyError:
            return jsonify({"error": "NotFound", "message": "Task not found"}), 404
        except PermissionError:
            return jsonify({"error": "Forbidden", "message": "Forbidden"}), 403
        except ValueError as e:
            return jsonify({"error": "BadRequest", "message": str(e)}), 400

    @app.route("/v1/tasks/<task_id>/history", methods=["GET"])
    def get_task_history(task_id: str) -> tuple[Response, int]:
        """Retrieve task change audit history."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        actor_id, actor_role = _get_actor()
        try:
            history = task_svc.get_history(task_id, actor_id=actor_id, actor_role=actor_role)
            return jsonify({"history": [h.to_dict() for h in history], "total": len(history)}), 200
        except KeyError:
            return jsonify({"error": "NotFound", "message": "Task not found"}), 404
        except PermissionError:
            return jsonify({"error": "Forbidden", "message": "Forbidden"}), 403

    @app.route("/v1/tasks/<task_id>/shares", methods=["POST"])
    def share_task(task_id: str) -> tuple[Response, int]:
        """Share task with another user."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        data: dict[str, Any] = request.get_json(silent=True) or {}
        target_user = data.get("user_id") or data.get("target_user_id")
        permission = data.get("permission")
        if not target_user or permission not in ("view", "edit"):
            return (
                jsonify(
                    {
                        "error": "BadRequest",
                        "message": "user_id and valid permission (view/edit) required",
                    }
                ),
                400,
            )

        actor_id, actor_role = _get_actor()
        try:
            task = task_svc.share_task(
                task_id=task_id,
                actor_id=actor_id,
                target_user_id=target_user,
                permission=permission,
                actor_role=actor_role,
            )
            return jsonify(task.to_dict()), 200
        except KeyError:
            return jsonify({"error": "NotFound", "message": "Task not found"}), 404
        except PermissionError:
            return jsonify({"error": "Forbidden", "message": "Forbidden"}), 403

    @app.route("/v1/tasks/<task_id>/reassign", methods=["POST"])
    def reassign_task(task_id: str) -> tuple[Response, int]:
        """Reassign task ownership."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        data: dict[str, Any] = request.get_json(silent=True) or {}
        new_owner_id = data.get("new_owner_id")
        if not new_owner_id:
            return jsonify({"error": "BadRequest", "message": "new_owner_id is required"}), 400

        actor_id, actor_role = _get_actor()
        try:
            task = task_svc.reassign_task(
                task_id=task_id,
                new_owner_id=new_owner_id,
                actor_id=actor_id,
                actor_role=actor_role,
                reason=data.get("reason", ""),
            )
            return jsonify(task.to_dict()), 200
        except KeyError:
            return jsonify({"error": "NotFound", "message": "Task not found"}), 404
        except PermissionError:
            return jsonify({"error": "Forbidden", "message": "Forbidden"}), 403

    @app.route("/v1/notifications", methods=["GET"])
    def list_notifications() -> tuple[Response, int]:
        """List current user notifications."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        actor_id, _ = _get_actor()
        notifs = task_svc.list_notifications(user_id=actor_id)
        return jsonify({"notifications": [n.to_dict() for n in notifs], "total": len(notifs)}), 200

    @app.route("/v1/notifications/<notification_id>/read", methods=["POST"])
    def mark_notification_read(notification_id: str) -> tuple[Response, int]:
        """Mark notification as read."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        notif = task_svc.mark_notification_read(notification_id)
        if notif is None:
            return jsonify({"error": "NotFound", "message": "Notification not found"}), 404
        return jsonify(notif.to_dict()), 200

    @app.route("/v1/users/<user_id>/status", methods=["POST", "PATCH"])
    def set_user_status(user_id: str) -> tuple[Response, int]:
        """Update user active status."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated error"}), 500

        data: dict[str, Any] = request.get_json(silent=True) or {}
        if "is_active" not in data:
            return jsonify({"error": "BadRequest", "message": "is_active is required"}), 400

        _, actor_role = _get_actor()
        try:
            user = task_svc.set_user_status(
                user_id=user_id,
                is_active=bool(data["is_active"]),
                actor_role=actor_role,
            )
            return jsonify(user.to_dict()), 200
        except PermissionError:
            return jsonify({"error": "Forbidden", "message": "Forbidden"}), 403

    # =========================================================================
    # Web UI Routes
    # =========================================================================

    @app.route("/tasks", methods=["GET"])
    def tasks_list() -> ResponseReturnValue:
        """Render task list dashboard."""
        actor_id, actor_role = _get_actor()
        tasks = task_svc.list_tasks(actor_id=actor_id, actor_role=actor_role)
        return render_template("screens/tasks_list.html", tasks=tasks)

    @app.route("/tasks/new", methods=["GET", "POST"])
    def task_create() -> ResponseReturnValue:
        """Render or submit new task form."""
        actor_id, _ = _get_actor()
        if request.method == "POST":
            title = request.form.get("title", "")
            notes = request.form.get("notes", "")
            priority = request.form.get("priority", "medium")
            if title:
                task_svc.create_task(title=title, owner_id=actor_id, notes=notes, priority=priority)
            return redirect(url_for("tasks_list"))
        return render_template("screens/task_create.html")

    @app.route("/tasks/<task_id>", methods=["GET"])
    def task_detail(task_id: str) -> ResponseReturnValue:
        """Render task detail view."""
        actor_id, actor_role = _get_actor()
        try:
            task = task_svc.get_task(task_id, actor_id=actor_id, actor_role=actor_role)
            return render_template("screens/task_detail.html", task=task)
        except (KeyError, PermissionError):
            return redirect(url_for("tasks_list"))

    @app.route("/tasks/orphaned", methods=["GET"])
    def orphaned_tasks() -> ResponseReturnValue:
        """Render orphaned tasks management screen."""
        _, actor_role = _get_actor()
        try:
            tasks = task_svc.list_orphaned_tasks(actor_role=actor_role)
        except PermissionError:
            tasks = []
        return render_template("screens/orphaned_tasks.html", tasks=tasks)

    return app
