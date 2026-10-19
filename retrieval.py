"""Runbook retrieval module.

Selects the most relevant runbook text for a given incident using simple
keyword-based scoring. No vector database, embeddings, or external services
are used.

The module reads Markdown runbooks from the ``runbooks/`` directory located
next to this file. Each runbook is scored against the incident's type and
description, and the best-matching runbook (or runbooks) is returned.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger("incident_api.retrieval")

# Directory containing Markdown runbooks — resolved relative to this file.
_RUNBOOKS_DIR = Path(__file__).resolve().parent / "runbooks"

# Maps incident types to the runbook filename that most directly covers them.
# This provides a fast, deterministic path for known incident types.
_INCIDENT_TYPE_TO_RUNBOOK = {
    "http_500": "http_500.md",
    "high_latency": "high_latency.md",
}


def _tokenise(text: str) -> set[str]:
    """Lowercase and split *text* into a set of keyword tokens."""
    # Split on non-alphanumeric characters and discard empties.
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t}


def load_runbooks(runbooks_dir: Path | None = None) -> list[dict]:
    """Load all Markdown runbooks from *runbooks_dir*.

    Returns a list of dicts, each with keys:
        ``name``      – the filename without ``.md``
        ``path``      – the full path as a string
        ``content``   – the raw Markdown text
    """
    directory = runbooks_dir or _RUNBOOKS_DIR
    runbooks: list[dict] = []

    if not directory.is_dir():
        logger.warning("Runbooks directory not found: %s", directory)
        return runbooks

    for path in sorted(directory.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not read runbook %s: %s", path, exc)
            continue
        runbooks.append(
            {
                "name": path.stem,
                "path": str(path),
                "content": content,
            }
        )
        logger.debug("Loaded runbook: %s", path.name)

    logger.info("Loaded %d runbook(s) from %s", len(runbooks), directory)
    return runbooks


def _score_runbook(runbook: dict, incident_type: str, description: str) -> int:
    """Score a runbook against the incident using keyword overlap.

    A higher score means a better match. The scoring is intentionally simple
    so it stays lightweight and easy to understand.
    """
    # Direct filename match for known incident types gets a big boost.
    expected_name = _INCIDENT_TYPE_TO_RUNBOOK.get(incident_type)
    if expected_name and runbook["name"] == Path(expected_name).stem:
        return 1000  # guaranteed top match

    # Otherwise score by keyword overlap between description and runbook content.
    description_tokens = _tokenise(description)
    runbook_tokens = _tokenise(runbook["content"])

    # Add incident type tokens into the description set for matching.
    description_tokens |= _tokenise(incident_type)

    overlap = description_tokens & runbook_tokens
    return len(overlap)


def retrieve_runbooks(
    incident_type: str,
    description: str,
    runbooks_dir: Path | None = None,
    top_k: int = 1,
) -> list[dict]:
    """Retrieve the *top_k* most relevant runbooks for the given incident.

    Each returned dict has:
        ``name``            – runbook filename without ``.md``
        ``path``            – full path to the runbook file
        ``content``         – the full Markdown text
        ``score``           – relevance score (higher = better)
    """
    runbooks = load_runbooks(runbooks_dir)
    if not runbooks:
        return []

    scored = []
    for rb in runbooks:
        score = _score_runbook(rb, incident_type, description)
        scored.append({**rb, "score": score})

    # Sort by score descending; break ties alphabetically by name.
    scored.sort(key=lambda r: (-r["score"], r["name"]))

    top = scored[:top_k]
    logger.info(
        "Retrieved %d runbook(s) for incident_type=%s; top match: %s (score=%d)",
        len(top),
        incident_type,
        top[0]["name"] if top else "none",
        top[0]["score"] if top else 0,
    )
    return top
