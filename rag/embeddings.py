"""Handles generation of embeddings from documents."""

import logging
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger("rag.embeddings")

_embedding_model = None


def get_embedding_model():
    """Return the local embedding model, loading it only once."""
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
        )
        logger.info("Embedding model loaded: all-MiniLM-L6-v2")

    return _embedding_model


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping character chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0:
        raise ValueError("overlap must be zero or greater")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized_text = " ".join(text.split())
    if not normalized_text:
        logger.info("Created 0 chunks")
        return []

    chunks = []
    start = 0
    text_length = len(normalized_text)
    step = chunk_size - overlap

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(normalized_text[start:end])
        if end == text_length:
            break
        start += step

    logger.info("Created %s chunks", len(chunks))
    return chunks


def load_document(file_path: str) -> str:
    """Read a text document, gracefully handling encoding issues."""
    path = Path(file_path)

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("UTF-8 decoding failed for %s; retrying with replacement characters", path)
        content = path.read_text(encoding="utf-8", errors="replace")

    logger.info("Loaded document %s with %s characters", path, len(content))
    return content
