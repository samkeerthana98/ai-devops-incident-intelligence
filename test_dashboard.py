"""Focused pytest tests for Phase 3 dashboard routes.

Tests cover the /dashboard route, incident display, and analysis triggered
from the dashboard. Ollama calls are mocked — no running model required.
"""

from unittest.mock import patch

import pytest

import app as app_module
from app import app
from ollama_client import OllamaError


@pytest.fixture()
def client():
    """Create a fresh test client and clear in-memory storage."""
    app_module.incidents.clear()
    app.testing = True
    return app.test_client()


# ---------------------------------------------------------------------------
# Dashboard page rendering
# ---------------------------------------------------------------------------

def test_dashboard_returns_html(client):
    """GET /dashboard should return 200 and HTML content."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    html = response.get_data(as_text=True)
    assert "AI DevOps Incident Intelligence" in html
    assert "Report New Incident" in html


def test_dashboard_shows_empty_state(client):
    """Dashboard should show an empty-state message when no incidents exist."""
    response = client.get("/dashboard")
    html = response.get_data(as_text=True)
    assert "No incidents recorded yet" in html or "Recorded Incidents" in html


def test_dashboard_shows_incidents_after_creation(client):
    """Dashboard should list incidents that have been created via the API."""
    client.post(
        "/api/incidents",
        json={
            "incident_type": "http_500",
            "description": "Checkout page 500 error.",
            "severity": "high",
        },
    )
    response = client.get("/dashboard")
    html = response.get_data(as_text=True)
    assert "http_500" in html
    assert "Checkout page 500 error." in html


def test_dashboard_contains_form_elements(client):
    """Dashboard should contain the form, severity dropdown, and analyze section."""
    response = client.get("/dashboard")
    html = response.get_data(as_text=True)
    assert 'id="incident-form"' in html
    assert 'id="incident_type"' in html
    assert 'id="severity"' in html
    assert 'id="description"' in html
    assert 'id="analysis-section"' in html


def test_dashboard_links_css_and_js(client):
    """Dashboard should link to the CSS and JS static files."""
    response = client.get("/dashboard")
    html = response.get_data(as_text=True)
    assert "dashboard.css" in html
    assert "dashboard.js" in html


# ---------------------------------------------------------------------------
# Dashboard analysis flow (mocked Ollama)
# ---------------------------------------------------------------------------

def test_dashboard_analyze_success(client):
    """Creating an incident then analyzing via API should work from the dashboard context."""
    # Create an incident
    create_resp = client.post(
        "/api/incidents",
        json={
            "incident_type": "high_latency",
            "description": "API p99 latency above 5 seconds.",
            "severity": "high",
        },
    )
    assert create_resp.status_code == 201
    incident_id = create_resp.get_json()["id"]

    mock_analysis = {
        "summary": "High latency detected on API endpoints.",
        "likely_cause": "Slow database queries.",
        "evidence": ["p99 above 5s", "DB query times elevated"],
        "recommendations": ["Add database indexes", "Enable query caching"],
    }

    with patch("app.analyze_incident", return_value=mock_analysis):
        response = client.post(f"/api/incidents/{incident_id}/analyze")

    assert response.status_code == 200
    data = response.get_json()
    assert data["summary"] == "High latency detected on API endpoints."
    assert "high_latency" in data["runbook_sources"]


def test_dashboard_analyze_ollama_unavailable(client):
    """When Ollama is down, the API should return 503 so the dashboard can show an error."""
    create_resp = client.post(
        "/api/incidents",
        json={
            "incident_type": "http_500",
            "description": "Payment service 500 errors.",
            "severity": "high",
        },
    )
    incident_id = create_resp.get_json()["id"]

    with patch("app.analyze_incident", side_effect=OllamaError("Could not connect to Ollama.")):
        response = client.post(f"/api/incidents/{incident_id}/analyze")

    assert response.status_code == 503
    assert "Could not connect to Ollama" in response.get_json()["error"]


def test_dashboard_analyze_missing_incident(client):
    """Analyzing a non-existent incident should return 404."""
    response = client.post("/api/incidents/does-not-exist/analyze")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Service info includes dashboard endpoint
# ---------------------------------------------------------------------------

def test_service_info_lists_dashboard(client):
    """GET / should now include the dashboard endpoint in the list."""
    response = client.get("/")
    data = response.get_json()
    assert "GET /dashboard" in data["endpoints"]
