"""
ChromaDB Database Connection

This file handles how our AI agents save and share their work. 
We use a vector database called ChromaDB.

How it works:
- All agents store their outputs in a single, shared "blitz_pipeline" bucket (collection).
- To make sure one user's pipeline doesn't accidentally read another user's data,
  every piece of data is tagged with a unique `run_id`.
- If an agent needs to be re-run, it just overwrites its old output using 
  an ID like `[run_id]::[agent_name]`.
"""

from __future__ import annotations

from typing import Any

import chromadb
from chromadb import Collection

_client: Any = None  # chromadb.PersistentClient instance (factory fn, not a class)
_collection: Collection | None = None


def get_collection() -> Collection:
    """
    Get (or create) the shared database collection.
    We only initialize the connection the very first time this is called,
    and then we reuse it to keep things fast!
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
    """
    Save what an agent just generated into the database.
    
    We use `upsert`, which means "update if it exists, insert if it doesn't".
    This is super helpful if an agent fails halfway through and we need to 
    retry it—it won't crash trying to save the same file twice.

    Args:
        run_id: The unique ID for this specific user's pipeline run.
        agent: Which agent is saving this? (e.g., "research", "profile")
        content: The actual text/JSON the agent generated.
        metadata: Any extra tags we want to attach to this saved file.
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
