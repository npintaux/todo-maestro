"""Production WSGI entrypoint for TaskFlow unified service."""

from __future__ import annotations

import os

from flask import Flask, Response, jsonify, redirect, request
from flask.typing import ResponseReturnValue

from modules.audit_service.entrypoints.app import create_audit_app
from modules.task_service.entrypoints.app import create_task_app


def create_app() -> Flask:
    """Create root Flask gateway application uniting task and audit services.

    Returns:
        Configured Flask instance with health probes and UI redirects.
    """
    app = create_task_app()
    audit_app = create_audit_app()

    @app.route("/healthz", methods=["GET"])
    def health_check() -> ResponseReturnValue:
        """Health check probe for Cloud Run, Kubernetes, and load balancers."""
        return jsonify({"status": "healthy", "service": "taskflow"}), 200

    @app.route("/", methods=["GET"])
    def index() -> ResponseReturnValue:
        """Redirect root path to tasks UI dashboard."""
        return redirect("/tasks")

    @app.route("/v1/audit/events", methods=["GET", "POST"])
    @app.route("/v1/audit/export", methods=["POST"])
    def audit_proxy() -> ResponseReturnValue:
        """Route audit events to audit service application.

        Returns:
            Proxied Flask response.
        """
        target_path = request.path
        if request.query_string:
            target_path = f"{request.path}?{request.query_string.decode('utf-8')}"
        with audit_app.test_client() as client:
            res = client.open(
                path=target_path,
                method=request.method,
                headers=dict(request.headers),
                data=request.get_data(),
            )
            return Response(res.get_data(), status=res.status_code, headers=dict(res.headers))

    return app


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
