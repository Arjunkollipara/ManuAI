"""Manages interaction with the vector database (ChromaDB)."""

import logging
import os
import shutil
from pathlib import Path

from langchain_chroma import Chroma

from rag.embeddings import chunk_text, get_embedding_model, load_document

logger = logging.getLogger("rag.vector_store")

_vector_store = None


def initialize_vector_store(
    documents_dir: str = "documents/",
    persist_dir: str = "data/vector_store/",
) -> Chroma:
    """Load maintenance documents, chunk them, and persist a Chroma vector store."""
    docs_path = Path(documents_dir)
    persist_path = Path(persist_dir)
    if persist_path.exists():
        shutil.rmtree(persist_path)
    persist_path.mkdir(parents=True, exist_ok=True)

    chunks = []
    metadatas = []

    if not docs_path.exists():
        raise FileNotFoundError(f"Documents directory not found: {docs_path}")

    for document_path in sorted(docs_path.glob("*.txt")):
        content = load_document(str(document_path))
        document_chunks = chunk_text(content)

        for chunk_index, chunk in enumerate(document_chunks):
            chunks.append(chunk)
            metadatas.append(
                {
                    "source": document_path.name,
                    "chunk_index": chunk_index,
                }
            )

    if not chunks:
        raise ValueError(f"No text chunks found in documents directory: {docs_path}")

    vector_store = Chroma.from_texts(
        texts=chunks,
        embedding=get_embedding_model(),
        metadatas=metadatas,
        persist_directory=str(persist_path),
    )

    if hasattr(vector_store, "persist"):
        vector_store.persist()

    logger.info("Total chunks indexed: %s", len(chunks))
    return vector_store


def load_vector_store(persist_dir: str = "data/vector_store/") -> Chroma:
    """Load an existing Chroma vector store, initializing it when missing."""
    persist_path = Path(persist_dir)

    if not persist_path.exists() or not any(persist_path.iterdir()):
        logger.info("Vector store not found at %s; initializing", persist_path)
        return initialize_vector_store(persist_dir=persist_dir)

    vector_store = Chroma(
        persist_directory=str(persist_path),
        embedding_function=get_embedding_model(),
    )

    try:
        if vector_store._collection.count() == 0:
            logger.info("Vector store at %s is empty; initializing", persist_path)
            return initialize_vector_store(persist_dir=persist_dir)
    except Exception as exc:
        logger.warning("Could not count vector store documents: %s", exc)

    logger.info("Loaded vector store from %s", persist_path)
    return vector_store


def get_vector_store() -> Chroma:
    """Return the process-wide vector store singleton."""
    global _vector_store

    if _vector_store is None:
        _vector_store = load_vector_store()

    return _vector_store


def get_azure_search_client():
    """
    Returns Azure AI Search client if credentials are configured, None otherwise.
    """
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_AI_SEARCH_KEY")
    index = os.getenv("AZURE_AI_SEARCH_INDEX", "manufacturing-docs")

    if not endpoint or not key:
        return None

    try:
        return SearchClient(
            endpoint=endpoint,
            index_name=index,
            credential=AzureKeyCredential(key),
        )
    except Exception as e:
        logger.warning("Azure Search unavailable: %s", e)
        return None


def get_vector_store_smart():
    """
    Returns Azure AI Search in production, ChromaDB in development.
    Automatic environment-based switching.
    """
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        client = get_azure_search_client()
        if client:
            logger.info("Using Azure AI Search (production)")
            return client, "azure"

    logger.info("Using ChromaDB (development)")
    return get_vector_store(), "chroma"
