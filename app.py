"""Minimal Flask application for simulated DevOps incident reporting.

Endpoints:
    GET  /                                  - service information
    GET  /health                            - JSON health status
    GET  /api/incidents                     - list recorded incidents
    POST /api/incidents                     - validate and record a simulated incident
    POST /api/incidents/<incident_id>/analyze - AI analysis of a recorded incident
"""

import logging
import os
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

from ollama_client import OllamaError, analyze_incident
from retrieval import retrieve_runbooks

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Basic logging — no secrets are recorded by this module.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("incident_api")

# The two incident types this service accepts.
VALID_INCIDENT_TYPES = ("http_500", "high_latency")

# Simple in-memory storage. A database is intentionally not used.
incidents: list[dict] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_response(message: str, status_code: int) -> tuple:
    """Build a consistent JSON error response."""
    return jsonify({"error": message}), status_code


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Return basic service information."""
    return jsonify(
        {
            "service": "ai-devops-incident-intelligence",
            "version": "1.0.0",
            "description": "Simulated DevOps incident reporting API.",
            "endpoints": [
                "GET /health",
                "GET /api/incidents",
                "POST /api/incidents",
                "POST /api/incidents/<incident_id>/analyze",
                "GET /dashboard",
            ],
        }
    )


@app.route("/health", methods=["GET"])
def health():
    """Return a JSON health status."""
    return jsonify({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()})


@app.route("/api/incidents", methods=["GET"])
def list_incidents():
    """Return every recorded incident."""
    logger.info("Listing incidents (count=%d)", len(incidents))
    return jsonify({"incidents": incidents, "count": len(incidents)})


@app.route("/api/incidents", methods=["POST"])
def create_incident():
    """Validate the request body and store a simulated incident.

    Required JSON fields:
        incident_type  - one of "http_500" or "high_latency"
        description    - non-empty string describing the incident
        severity       - one of "low", "medium", "high" (optional, default "medium")
    """
    data = request.get_json(silent=True)

    if data is None or not isinstance(data, dict):
        logger.warning("Rejected request: missing or invalid JSON body")
        return _error_response("Request body must be valid JSON.", 400)

    incident_type = data.get("incident_type")
    description = data.get("description")
    severity = data.get("severity", "medium")

    # --- incident_type ----------------------------------------------------
    if not incident_type or not isinstance(incident_type, str):
        logger.warning("Rejected request: missing incident_type")
        return _error_response("'incident_type' is required and must be a string.", 400)

    if incident_type not in VALID_INCIDENT_TYPES:
        logger.warning("Rejected request: unknown incident_type '%s'", incident_type)
        return (
            _error_response(
                f"'incident_type' must be one of: {', '.join(VALID_INCIDENT_TYPES)}.",
                400,
            )
        )

    # --- description ------------------------------------------------------
    if not description or not isinstance(description, str) or not description.strip():
        logger.warning("Rejected request: missing or empty description")
        return _error_response("'description' is required and must be a non-empty string.", 400)

    # --- severity ---------------------------------------------------------
    valid_severities = ("low", "medium", "high")
    if severity not in valid_severities:
        logger.warning("Rejected request: invalid severity '%s'", severity)
        return _error_response(f"'severity' must be one of: {', '.join(valid_severities)}.", 400)

    # --- store ------------------------------------------------------------
    incident = {
        "id": str(uuid.uuid4()),
        "incident_type": incident_type,
        "description": description.strip(),
        "severity": severity,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    incidents.append(incident)
    logger.info(
        "Recorded incident id=%s type=%s severity=%s",
        incident["id"],
        incident["incident_type"],
        incident["severity"],
    )

    return jsonify(incident), 201


# ---------------------------------------------------------------------------
# Incident analysis
# ---------------------------------------------------------------------------

@app.route("/api/incidents/<incident_id>/analyze", methods=["POST"])
def analyze_incident_endpoint(incident_id: str):
    """Analyze a recorded incident using AI with runbook retrieval.

    Steps:
        1. Find the incident by ID.
        2. Retrieve the most relevant runbook.
        3. Request AI analysis from Ollama.
        4. Return structured JSON with analysis and runbook sources.

    The model's output is advisory only — no commands are executed.
    """
    # --- find incident ----------------------------------------------------
    incident = next((i for i in incidents if i["id"] == incident_id), None)
    if incident is None:
        logger.warning("Analyze: incident not found id=%s", incident_id)
        return _error_response(f"Incident '{incident_id}' not found.", 404)

    # --- retrieve runbooks ------------------------------------------------
    runbooks = retrieve_runbooks(
        incident_type=incident["incident_type"],
        description=incident["description"],
    )

    if runbooks:
        runbook_text = runbooks[0]["content"]
        runbook_sources = [rb["name"] for rb in runbooks]
    else:
        runbook_text = "No runbook available for this incident type."
        runbook_sources = []

    logger.info(
        "Analyze: incident_id=%s runbook_sources=%s",
        incident_id,
        runbook_sources,
    )

    # --- request AI analysis ----------------------------------------------
    try:
        analysis = analyze_incident(incident, runbook_text)
    except OllamaError as exc:
        logger.error("Analyze: Ollama error for incident_id=%s: %s", incident_id, exc)
        return _error_response(str(exc), 503)

    # --- build response ---------------------------------------------------
    response = {
        "incident_id": incident_id,
        "summary": analysis.get("summary", ""),
        "likely_cause": analysis.get("likely_cause", ""),
        "evidence": analysis.get("evidence", []),
        "recommendations": analysis.get("recommendations", []),
        "runbook_sources": runbook_sources,
    }

    return jsonify(response), 200


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Render the HTML dashboard with the current incident list."""
    logger.info("Rendering dashboard (incident_count=%d)", len(incidents))
    return render_template("dashboard.html", incidents=incidents)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
