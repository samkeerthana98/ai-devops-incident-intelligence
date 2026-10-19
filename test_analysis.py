"""Focused pytest tests for Phase 2 incident analysis.

These tests do NOT require a running Ollama instance. The Ollama HTTP call is
mocked using unittest.mock so no real network calls are made.
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


@pytest.fixture()
def created_incident(client):
    """Create an incident and return its ID for analysis tests."""
    response = client.post(
        "/api/incidents",
        json={
            "incident_type": "http_500",
            "description": "Checkout page returning 500 errors intermittently.",
            "severity": "high",
        },
    )
    assert response.status_code == 201
    return response.get_json()["id"]


# ---------------------------------------------------------------------------
# Retrieval module tests
# ---------------------------------------------------------------------------

def test_retrieval_returns_matching_runbook():
    """Retrieval should return the runbook that matches the incident type."""
    from retrieval import retrieve_runbooks

    results = retrieve_runbooks(
        incident_type="http_500",
        description="Checkout page returning 500 errors.",
    )
    assert len(results) >= 1
    assert results[0]["name"] == "http_500"
    assert "content" in results[0]
    assert "500" in results[0]["content"]


def test_retrieval_returns_high_latency_runbook():
    """Retrieval should return the high_latency runbook for latency incidents."""
    from retrieval import retrieve_runbooks

    results = retrieve_runbooks(
        incident_type="high_latency",
        description="API p99 latency above 2 seconds.",
    )
    assert len(results) >= 1
    assert results[0]["name"] == "high_latency"
    assert "latency" in results[0]["content"].lower()


def test_retrieval_returns_general_for_unknown_type():
    """For an unknown incident type, retrieval should still return a runbook."""
    from retrieval import retrieve_runbooks

    results = retrieve_runbooks(
        incident_type="unknown",
        description="Service is behaving unexpectedly.",
    )
    assert len(results) >= 1
    # Should return the general troubleshooting runbook (highest keyword overlap).
    assert results[0]["name"] == "general_troubleshooting"


# ---------------------------------------------------------------------------
# Analyze endpoint — success with mocked Ollama
# ---------------------------------------------------------------------------

def test_analyze_success(client, created_incident):
    """POST /api/incidents/<id>/analyze should return structured analysis."""
    mock_analysis = {
        "summary": "Intermittent 500 errors on the checkout page.",
        "likely_cause": "Database connection pool exhaustion during peak traffic.",
        "evidence": ["500 errors correlate with traffic spikes", "DB pool at capacity"],
        "recommendations": ["Increase connection pool size", "Add retry logic"],
    }

    with patch("app.analyze_incident", return_value=mock_analysis):
        response = client.post(f"/api/incidents/{created_incident}/analyze")

    assert response.status_code == 200
    data = response.get_json()
    assert data["incident_id"] == created_incident
    assert data["summary"] == mock_analysis["summary"]
    assert data["likely_cause"] == mock_analysis["likely_cause"]
    assert data["evidence"] == mock_analysis["evidence"]
    assert data["recommendations"] == mock_analysis["recommendations"]
    assert "http_500" in data["runbook_sources"]


# ---------------------------------------------------------------------------
# Analyze endpoint — missing incident
# ---------------------------------------------------------------------------

def test_analyze_incident_not_found(client):
    """Analyzing a non-existent incident should return 404."""
    response = client.post("/api/incidents/nonexistent-id/analyze")
    assert response.status_code == 404
    assert "error" in response.get_json()


# ---------------------------------------------------------------------------
# Analyze endpoint — Ollama unavailable
# ---------------------------------------------------------------------------

def test_analyze_ollama_failure(client, created_incident):
    """When Ollama is unavailable, the endpoint should return 503."""
    with patch("app.analyze_incident", side_effect=OllamaError("Could not connect to Ollama.")):
        response = client.post(f"/api/incidents/{created_incident}/analyze")

    assert response.status_code == 503
    data = response.get_json()
    assert "error" in data
    assert "Could not connect to Ollama" in data["error"]


def test_analyze_ollama_timeout(client, created_incident):
    """When Ollama times out, the endpoint should return 503."""
    with patch("app.analyze_incident", side_effect=OllamaError("Ollama request timed out.")):
        response = client.post(f"/api/incidents/{created_incident}/analyze")

    assert response.status_code == 503
    assert "timed out" in response.get_json()["error"]


# ---------------------------------------------------------------------------
# Analyze endpoint — malformed model response
# ---------------------------------------------------------------------------

def test_analyze_malformed_response(client, created_incident):
    """When Ollama returns unparseable output, the endpoint should return 503."""
    with patch(
        "app.analyze_incident",
        side_effect=OllamaError("Ollama returned a malformed response that could not be parsed."),
    ):
        response = client.post(f"/api/incidents/{created_incident}/analyze")

    assert response.status_code == 503
    assert "malformed" in response.get_json()["error"].lower()


# ---------------------------------------------------------------------------
# Regression test — ID round-trip (guards against the multi-worker storage bug)
# ---------------------------------------------------------------------------

def test_create_then_analyze_uses_returned_id(client):
    """An incident's returned ID must work for analysis without a 404.

    Regression guard: with multiple gunicorn workers, each worker holds its own
    in-memory incidents list. An incident created on worker A is not visible to
    worker B, so analyze returns 404. The fix is --workers 1 in gunicorn.

    In this test the Flask test client is single-process, so the round-trip
    always works — confirming the application logic itself is correct and that
    the ID returned by POST /api/incidents is the exact key used by the analyze
    endpoint.
    """
    # Step 1: create an incident and capture the ID the API returns.
    create_resp = client.post(
        "/api/incidents",
        json={
            "incident_type": "http_500",
            "description": "Checkout service returning 500 errors.",
            "severity": "high",
        },
    )
    assert create_resp.status_code == 201
    returned_id = create_resp.get_json()["id"]
    assert returned_id  # must be a non-empty string

    # Step 2: confirm the incident appears in the list with the same ID.
    list_resp = client.get("/api/incidents")
    assert list_resp.status_code == 200
    ids_in_list = [i["id"] for i in list_resp.get_json()["incidents"]]
    assert returned_id in ids_in_list, (
        f"ID {returned_id!r} from POST not found in GET /api/incidents response"
    )

    # Step 3: analyze using the returned ID — must not return 404.
    mock_analysis = {
        "summary": "500 errors on checkout.",
        "likely_cause": "Database overload.",
        "evidence": ["high error rate"],
        "recommendations": ["restart service"],
    }
    with patch("app.analyze_incident", return_value=mock_analysis):
        analyze_resp = client.post(f"/api/incidents/{returned_id}/analyze")

    assert analyze_resp.status_code == 200, (
        f"Expected 200, got {analyze_resp.status_code}: "
        f"{analyze_resp.get_json()}"
    )
    data = analyze_resp.get_json()
    assert data["incident_id"] == returned_id


# ---------------------------------------------------------------------------
# Ollama client — response parsing unit tests
# ---------------------------------------------------------------------------

def test_parse_model_response_valid():
    """_parse_model_response should parse valid JSON correctly."""
    from ollama_client import _parse_model_response

    raw = '{"summary": "test", "likely_cause": "cause", "evidence": ["e"], "recommendations": ["r"]}'
    result = _parse_model_response(raw)
    assert result is not None
    assert result["summary"] == "test"
    assert result["evidence"] == ["e"]


def test_parse_model_response_with_code_fence():
    """_parse_model_response should strip markdown code fences."""
    from ollama_client import _parse_model_response

    raw = '```json\n{"summary": "fenced", "likely_cause": "x", "evidence": [], "recommendations": []}\n```'
    result = _parse_model_response(raw)
    assert result is not None
    assert result["summary"] == "fenced"


def test_parse_model_response_invalid():
    """_parse_model_response should return None for invalid JSON."""
    from ollama_client import _parse_model_response

    assert _parse_model_response("not json at all") is None
    assert _parse_model_response("") is None
