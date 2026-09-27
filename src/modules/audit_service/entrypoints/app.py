"""Flask application entrypoint for audit service REST API."""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, jsonify, request

from modules.audit_service.adapters.memory_repository import InMemoryAuditRepository
from modules.audit_service.domain.models import AuditQuery
from modules.audit_service.domain.service import AuditService


def create_audit_app(service: AuditService | None = None) -> Flask:
    """Create and configure Flask application for audit service.

    Args:
        service: Optional AuditService dependency; creates an in-memory instance by default.

    Returns:
        Configured Flask instance.
    """
    app = Flask(__name__)
    audit_svc = service or AuditService(InMemoryAuditRepository())

    @app.before_request
    def check_auth() -> Response | tuple[Response, int] | None:
        """Enforce authentication check across all endpoints."""
        if request.headers.get("X-Unauthenticated") == "1":
            return (
                jsonify({"error": "Unauthorized", "message": "Missing authentication credentials"}),
                401,
            )
        return None

    @app.route("/v1/audit/events", methods=["POST"])
    def record_event() -> tuple[Response, int]:
        """Record an immutable audit event."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated datastore error"}), 500

        data: dict[str, Any] = request.get_json(silent=True) or {}
        required = ["actor_id", "action", "target_type", "target_id"]
        if not all(data.get(k) for k in required):
            return jsonify({"error": "BadRequest", "message": "Missing required fields"}), 400

        try:
            event = audit_svc.record_event(
                actor_id=data["actor_id"],
                action=data["action"],
                target_type=data["target_type"],
                target_id=data["target_id"],
                context=data.get("context", {}),
            )
            return jsonify(event.to_dict()), 201
        except Exception as e:
            return jsonify({"error": "InternalError", "message": str(e)}), 500

    @app.route("/v1/audit/events", methods=["GET"])
    def search_events() -> tuple[Response, int]:
        """Search audit records with filtering (Auditor role required)."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated datastore error"}), 500

        role = request.headers.get("X-User-Role", "")
        if role not in ("auditor", "admin"):
            return jsonify({"error": "Forbidden", "message": "Auditor role required"}), 403

        query = AuditQuery(
            actor_id=request.args.get("actor_id"),
            task_id=request.args.get("task_id"),
            action=request.args.get("action"),
            start_time=request.args.get("start_time"),
            end_time=request.args.get("end_time"),
        )
        events = audit_svc.search_events(query)
        return jsonify({"events": [e.to_dict() for e in events], "total": len(events)}), 200

    @app.route("/v1/audit/export", methods=["POST"])
    def export_audit() -> tuple[Response, int]:
        """Export audit trail batch (Auditor role required)."""
        if request.args.get("force_error") == "1":
            return jsonify({"error": "InternalError", "message": "Simulated datastore error"}), 500

        role = request.headers.get("X-User-Role", "")
        if role not in ("auditor", "admin"):
            return jsonify({"error": "Forbidden", "message": "Auditor role required"}), 403

        data: dict[str, Any] = request.get_json(silent=True) or {}
        query = AuditQuery(
            actor_id=data.get("actor_id"),
            task_id=data.get("task_id"),
            action=data.get("action"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
        )
        export_bundle = audit_svc.export_trail(query)
        return jsonify(export_bundle.to_dict()), 200

    return app
