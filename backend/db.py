"""ChromaDB PersistentClient singleton — run_id-scoped document storage.

Design decisions:
- Single shared ChromaDB client and collection (module-level singletons)
- ONE collection ("blitz_pipeline") with metadata filtering for run_id isolation,
  NOT separate collections per run — avoids collection proliferation and ChromaDB
  limits, and makes cross-run queries easy if needed in the future
- Document IDs are "{run_id}::{agent}" — deterministic, enables upsert semantics
  so re-running an agent within the same run safely overwrites instead of crashing
- PersistentClient path is "./chroma_data" — this directory is gitignored
- Run isolation is enforced by where={"run_id": run_id} in all queries;
  a second run_id cannot retrieve the first run's documents
- chromadb.PersistentClient is a factory function (not a class) in chromadb 1.x,
  so we annotate the module-level singleton with Any to avoid TypeError on |
"""

from __future__ import annotations

from typing import Any

import chromadb
from chromadb import Collection

_client: Any = None  # chromadb.PersistentClient instance (factory fn, not a class)
_collection: Collection | None = None


def get_collection() -> Collection:
    """Get or create the shared blitz_pipeline collection.

    Initializes the ChromaDB PersistentClient on first call. Subsequent calls
    return the cached collection without I/O.
    """
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path="./chroma_data")
        _collection = _client.get_or_create_collection("blitz_pipeline")
    return _collection


def store_agent_output(
    run_id: str,
    agent: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    """Store an agent's output scoped to a run_id.

    Uses upsert so re-running the same agent within the same run safely
    overwrites the previous output without raising a duplicate ID error.

    Args:
        run_id: The pipeline run identifier (UUID4).
        agent: The agent name/key (e.g. "research", "profile").
        content: The serialized agent output to store.
        metadata: Optional additional metadata fields to attach to the document.
    """
    col = get_collection()
    meta: dict = {"run_id": run_id, "agent": agent}
    if metadata:
        meta.update(metadata)
    col.upsert(
        documents=[content],
        metadatas=[meta],
        ids=[f"{run_id}::{agent}"],
    )


def get_run_context(run_id: str) -> list[str]:
    """Retrieve all documents stored for a given run_id.

    Cannot see documents from other runs — the where filter enforces isolation.

    Args:
        run_id: The pipeline run identifier to retrieve documents for.

    Returns:
        List of document strings for this run, in storage order.
        Returns an empty list if no documents exist for this run_id.
    """
    col = get_collection()
    result = col.get(where={"run_id": run_id})
    return result["documents"] if result["documents"] else []


def get_agent_output(run_id: str, agent: str) -> str | None:
    """Retrieve a specific agent's output for a run_id.

    Args:
        run_id: The pipeline run identifier.
        agent: The agent name/key used when storing.

    Returns:
        The stored document string, or None if not found.
    """
    col = get_collection()
    result = col.get(ids=[f"{run_id}::{agent}"])
    if result["documents"]:
        return result["documents"][0]
    return None
