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

import json
from typing import Any

import chromadb
from chromadb import Collection
from chromadb.api.types import EmbeddingFunction

from app.config import settings


class _NoopEmbedding(EmbeddingFunction):
    """Placeholder embedding used when similarity search is switched off.

    Chroma requires an embedding function even when documents are only ever
    fetched by id. Returning a constant skips the ONNX model entirely.
    """

    def __init__(self) -> None:  # noqa: D107 - required by chromadb
        pass

    def __call__(self, input):  # noqa: A002 - name fixed by the chromadb interface
        return [[0.0] for _ in input]

    @staticmethod
    def name() -> str:
        return "noop"

    def get_config(self) -> dict:
        """Serialised form, persisted with the collection by chromadb."""
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "_NoopEmbedding":
        return _NoopEmbedding()


_client: Any = None  # chromadb client instance (factory fn, not a class)
_collection: Collection | None = None


def get_collection() -> Collection:
    """
    Get (or create) the shared database collection.
    We only initialize the connection the very first time this is called,
    and then we reuse it to keep things fast!

    The path is resolved absolutely from settings, so launching the app from a
    different working directory reuses the same store instead of silently
    creating a second one. Tests set CHROMA_IN_MEMORY to get an ephemeral client,
    which needs no files and cannot hit the file-locking races a persistent
    client suffers on Windows.
    """
    global _client, _collection
    if _collection is None:
        if settings.chroma_in_memory:
            _client = chromadb.EphemeralClient()
        else:
            _client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        kwargs = {}
        if settings.chroma_disable_embeddings:
            kwargs["embedding_function"] = _NoopEmbedding()
        _collection = _client.get_or_create_collection(settings.chroma_collection, **kwargs)
    return _collection


def reset_client() -> None:
    """Drop the cached client and collection.

    Only for tests, which need a clean store between cases.
    """
    global _client, _collection
    _client = None
    _collection = None


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


# ---------------------------------------------------------------------------
# Prompt-facing reads
# ---------------------------------------------------------------------------

# site_content is the raw scraped page, and it's about 80% of the research
# output. Every later agent pastes that whole JSON into its prompt, so without
# trimming we send the same page to the model five times a run. Agent 0 already
# boils it down into summary and executive_summary, which is what the others
# actually read. The full copy stays in the database either way.
_PROMPT_TRIMMED_FIELDS: dict[str, int] = {"site_content": settings.site_content_prompt_chars}


def get_agent_context(run_id: str, agent: str) -> str | None:
    """Retrieve an agent's output, trimmed for use inside a downstream prompt.

    Identical to get_agent_output() except that oversized raw fields are cut to
    an excerpt. Use this when building a prompt; use get_agent_output() when the
    complete stored artifact is what you want.

    Args:
        run_id: The pipeline run identifier.
        agent: The agent name/key used when storing.

    Returns:
        The stored document with large fields truncated, or None if not found.
        Returns the document unchanged if it is not a JSON object.
    """
    raw = get_agent_output(run_id, agent)
    if raw is None:
        return None

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return raw
    if not isinstance(data, dict):
        return raw

    trimmed = False
    for field, limit in _PROMPT_TRIMMED_FIELDS.items():
        value = data.get(field)
        if isinstance(value, str) and len(value) > limit:
            note = f"[...truncated for prompt use, {len(value)} chars total]"
            data[field] = f"{value[:limit]}\n{note}"
            trimmed = True

    return json.dumps(data) if trimmed else raw
