"""Shared fixtures.

No test in here should hit the network or a real LLM. These fixtures keep it
that way so the suite stays fast and free to run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Must be set before litellm is imported anywhere. Without it litellm fetches its
# model cost map from GitHub on import, which makes the suite reach the network,
# fail on an offline machine, and hang in CI without egress.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import pytest  # noqa: E402

# Make the backend package importable regardless of where pytest is invoked from.
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@pytest.fixture(autouse=True)
def _no_real_api_keys(monkeypatch):
    """Point every provider credential at an obvious dummy.

    If a test ever does reach the network, it fails on auth rather than quietly
    spending money against the developer's real key.
    """
    for var in ("OPENAI_API_KEY", "GEMINI_API_KEY", "TAVILY_API_KEY", "FIRECRAWL_API_KEY"):
        monkeypatch.setenv(var, f"test-dummy-{var.lower()}")


@pytest.fixture
def research_payload() -> dict:
    """A ResearchOutput-shaped dict with an oversized site_content field."""
    return {
        "company_name": "Acme",
        "company_url": "https://acme.com",
        "summary": "Acme builds widgets.",
        "executive_summary": "Acme leads the widget category.",
        "press_coverage": [{"title": "Acme raises", "url": "https://x.com/a", "snippet": "..."}],
        "site_content": "x" * 40_000,
        "competitors": [{"name": "Globex", "positioning": "cheap", "strengths": [], "weaknesses": []}],
        "aeo_score": 7.5,
        "aeo_details": [{"model": "openai/gpt-4o", "mentioned": True, "mention_rate": "3/3"}],
    }


@pytest.fixture
def isolated_chroma(monkeypatch):
    """Give each test a private, in-memory ChromaDB.

    Two reasons this is in-memory rather than a temp directory. It keeps tests
    away from the developer's real chroma_data, and a PersistentClient per test
    hits file-locking races on Windows that made the suite intermittently fail
    and swing between 20s and 125s.
    """
    import app.db.chroma as db
    from app.config import settings

    monkeypatch.setattr(settings, "chroma_in_memory", True)
    # Blitz never runs a similarity query, so the default ONNX embedding model
    # is pure overhead here — it was costing several seconds per test.
    monkeypatch.setattr(settings, "chroma_disable_embeddings", True)
    db.reset_client()
    yield
    db.reset_client()
