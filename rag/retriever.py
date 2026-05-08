"""Handles document retrieval based on queries."""

import logging

from langchain_chroma import Chroma

from rag.vector_store import get_vector_store

logger = logging.getLogger("rag.retriever")


def retrieve_documents(query: str, vector_store: Chroma, k: int = 3) -> list[dict]:
    """Run similarity search and return normalized document result dictionaries."""
    if not query or not query.strip():
        return []

    raw_results = vector_store.similarity_search_with_score(query.strip(), k=k)
    results = []

    for document, distance in raw_results:
        metadata = document.metadata or {}
        try:
            relevance_score = 1.0 / (1.0 + max(0.0, float(distance)))
        except Exception:
            relevance_score = 0.0
        results.append(
            {
                "content": document.page_content,
                "source": metadata.get("source", "unknown"),
                "relevance_score": relevance_score,
            }
        )

    logger.info("Retrieved %s results for query: %s", len(results), query)
    return results


def format_context(retrieved_docs: list[dict]) -> str:
    """Format retrieved documents as a single context block."""
    context_blocks = []

    for doc in retrieved_docs:
        context_blocks.append(
            f"Source: {doc['source']}\n"
            f"Content: {doc['content']}\n"
            "---"
        )

    return "\n".join(context_blocks)


def search_maintenance_docs(query: str, k: int = 3) -> dict:
    """Search maintenance documents and return API-ready RAG results."""
    if not query or not query.strip():
        return {
            "query": "",
            "results": [],
            "formatted_context": "",
            "total_results": 0,
            "status": "EMPTY_QUERY",
        }

    try:
        vector_store = get_vector_store()
        results = retrieve_documents(query=query, vector_store=vector_store, k=k)
        formatted_context = format_context(results)

        return {
            "query": query,
            "results": results,
            "formatted_context": formatted_context,
            "total_results": len(results),
            "status": "SUCCESS",
        }
    except Exception as exc:
        logger.error("Document search failed: %s", exc)
        return {
            "query": query,
            "results": [],
            "formatted_context": "",
            "total_results": 0,
            "status": "ERROR",
            "error": str(exc),
        }
