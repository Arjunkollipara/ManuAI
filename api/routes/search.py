"""API routes for RAG and search functionality."""

import logging

from fastapi import APIRouter, Query

from rag.retriever import search_maintenance_docs
from rag.vector_store import get_vector_store

router = APIRouter()
logger = logging.getLogger("api.routes.search")


@router.get("/documents")
def search_documents(
    q: str | None = Query(default=None),
    limit: int = Query(5, ge=1, le=20),
):
    """Search for documents using the RAG pipeline."""
    try:
        query = (q or "").strip()
        if not query:
            return {
                "query": "",
                "results": [],
                "formatted_context": "",
                "total_results": 0,
                "status": "EMPTY_QUERY",
            }

        logger.info("Search requested: query='%s', limit=%s", query, limit)

        response = search_maintenance_docs(query=query, k=limit)

        logger.info("Search completed: query='%s', results=%s", query, response["total_results"])
        return response

    except Exception as e:
        logger.error("Error in document search: %s", e)
        return {
            "query": q or "",
            "results": [],
            "formatted_context": "",
            "total_results": 0,
            "status": "ERROR",
            "error": str(e)
        }


@router.get("/documents/health")
def search_health():
    """Check RAG pipeline health status."""
    try:
        logger.info("Search health check requested")

        vector_store = get_vector_store()
        documents_indexed = vector_store._collection.count()

        response = {
            "rag_initialized": True,
            "vector_store": "ChromaDB",
            "documents_indexed": documents_indexed,
            "status": "HEALTHY",
        }

        logger.info("Search health check completed")
        return response

    except Exception as e:
        logger.error("Error in search health check: %s", e)
        return {
            "rag_initialized": False,
            "vector_store": "ChromaDB",
            "documents_indexed": 0,
            "status": "ERROR",
            "error": str(e)
        }
