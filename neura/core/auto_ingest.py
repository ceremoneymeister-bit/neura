"""
Auto-ingest: parse uploaded documents → chunk → embed → memory.

Integrates with existing MemoryStore.add_memory() and vectordb._chunk_text().
Called from telegram._handle_document() and web.upload_file() after file save.
"""

from __future__ import annotations

import logging
from pathlib import Path

from neura.core.vectordb import _chunk_text
from neura.core.document_processor import parse_document, parse_url, _URL_PATTERN

logger = logging.getLogger(__name__)

# Max chars to ingest per document (prevent runaway embedding cost)
MAX_INGEST_CHARS = 200_000


async def ingest_document(
    memory,
    capsule_id: str,
    file_path_or_url: str,
    filename: str,
    *,
    markdown_text: str | None = None,
) -> int:
    """Parse a document and save chunks to long-term memory.

    Args:
        memory:             MemoryStore instance (has add_memory method)
        capsule_id:         Capsule identifier
        file_path_or_url:   Local file path or https:// URL
        filename:           Human-readable name (used in source tag and chunking)
        markdown_text:      Pre-parsed markdown (skip parsing if provided)

    Returns:
        Number of chunks saved (0 on failure or empty document)
    """
    if memory is None:
        return 0

    # --- 1. Parse if not already provided ---
    if markdown_text is None:
        if _URL_PATTERN.match(file_path_or_url):
            markdown_text = parse_url(file_path_or_url)
        else:
            markdown_text = parse_document(file_path_or_url)

    if not markdown_text or not markdown_text.strip():
        logger.debug(f"auto_ingest: empty content for {filename}, skipping")
        return 0

    # Truncate to prevent excessive memory usage
    if len(markdown_text) > MAX_INGEST_CHARS:
        markdown_text = markdown_text[:MAX_INGEST_CHARS]
        logger.info(f"auto_ingest: truncated {filename} to {MAX_INGEST_CHARS} chars")

    # --- 2. Chunk ---
    source_tag = f"document:{Path(filename).name}"
    chunks = _chunk_text(markdown_text, source=source_tag)
    if not chunks:
        logger.debug(f"auto_ingest: no chunks for {filename}")
        return 0

    # --- 3. Embed + save to pgvector memory ---
    saved = 0
    for chunk in chunks:
        try:
            await memory.add_memory(
                capsule_id,
                chunk["text"],
                source=source_tag,
            )
            saved += 1
        except Exception as e:
            logger.warning(f"auto_ingest: failed to save chunk {saved} of {filename}: {e}")

    logger.info(f"auto_ingest: {filename} → {saved}/{len(chunks)} chunks in memory [{capsule_id}]")
    return saved
