"""Focused pytest tests for the incident API.

These tests use Flask's built-in test client so no network server is required.
"""

import pytest

from app import app


@pytest.fixture()
def client():
    """Create a fresh test client and clear in-memory storage for each test."""
    import app as app_module

    app_module.incidents.clear()
    app.testing = True
    return app.test_client()


# ---------------------------------------------------------------------------
# Service information & health
# ---------------------------------------------------------------------------

def test_index_returns_service_info(client):
    """GET / should return service metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["service"] == "ai-devops-incident-intelligence"
    assert "endpoints" in data


def test_health_returns_healthy_status(client):
    """GET /health should return a healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


# ---------------------------------------------------------------------------
# Incident listing
# ---------------------------------------------------------------------------

def test_list_incidents_empty(client):
    """GET /api/incidents with no records should return an empty list."""
    response = client.get("/api/incidents")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0
    assert data["incidents"] == []


def test_list_incidents_after_creation(client):
    """After creating an incident it should appear in the list."""
    payload = {
        "incident_type": "http_500",
        "description": "Checkout page returned 500",
        "severity": "high",
    }
    client.post("/api/incidents", json=payload)

    response = client.get("/api/incidents")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    assert data["incidents"][0]["incident_type"] == "http_500"


# ---------------------------------------------------------------------------
# Valid incident creation
# ---------------------------------------------------------------------------

def test_create_incident_http_500(client):
    """POST a valid http_500 incident should return 201 with the stored record."""
    payload = {
        "incident_type": "http_500",
        "description": "Payment service returned 500 errors.",
        "severity": "high",
    }
    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["incident_type"] == "http_500"
    assert data["description"] == "Payment service returned 500 errors."
    assert data["severity"] == "high"
    assert "id" in data
    assert "created_at" in data


def test_create_incident_high_latency_default_severity(client):
    """Severity is optional and should default to 'medium'."""
    payload = {
        "incident_type": "high_latency",
        "description": "API p99 latency above 2 seconds.",
    }
    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["incident_type"] == "high_latency"
    assert data["severity"] == "medium"


# ---------------------------------------------------------------------------
# Invalid input
# ---------------------------------------------------------------------------

def test_create_incident_missing_json_body(client):
    """POST without a JSON body should return 400."""
    response = client.post("/api/incidents", data="not json", content_type="text/plain")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_incident_invalid_type(client):
    """An unknown incident_type should be rejected."""
    payload = {
        "incident_type": "disk_full",
        "description": "Disk almost full.",
    }
    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_incident_missing_description(client):
    """A missing description should be rejected."""
    payload = {"incident_type": "http_500", "severity": "low"}
    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_incident_invalid_severity(client):
    """An invalid severity value should be rejected."""
    payload = {
        "incident_type": "http_500",
        "description": "Intermittent 500 on /api/orders.",
        "severity": "critical",
    }
    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 400
    assert "error" in response.get_json()
