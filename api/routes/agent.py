"""API routes interacting with AI agents."""

import logging
from fastapi import APIRouter
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

from agents.crew import check_credentials, process_question

router = APIRouter()
logger = logging.getLogger("api.routes.agent")


class AgentQuery(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = None


@router.post("/query")
def query_agent(request: AgentQuery):
    """Query the multi-agent orchestration layer."""
    try:
        logger.info(f"Agent query received: question='{request.question}'")
        result = process_question(request.question, request.context)
        response = {
            "question": request.question,
            "answer": result.get("answer", ""),
            "agent_used": result.get("agent_used", "none"),
            "sources": result.get("sources", []),
            "status": result.get("status", "ERROR"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        logger.info("Agent query completed: status=%s", response["status"])
        return response
    except Exception as e:
        logger.error(f"Error in agent query: {e}")
        return {
            "question": request.question,
            "answer": f"Error: {str(e)}",
            "agent_used": "none",
            "sources": [],
            "status": "ERROR",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


@router.get("/status")
def agent_status():
    """Get status of available agents."""
    try:
        logger.info("Agent status check requested")
        creds_ready = check_credentials()
        response = {
            "agents_initialized": creds_ready,
            "available_agents": [
                "MaintenanceAgent",
                "AnalyticsAgent",
                "MLInsightAgent",
            ],
            "orchestration": "CrewAI",
            "credentials_configured": creds_ready,
            "status": "READY" if creds_ready else "CREDENTIALS_REQUIRED",
        }
        logger.info("Agent status check completed")
        return response
    except Exception as e:
        logger.error(f"Error in agent status check: {e}")
        return {
            "agents_initialized": False,
            "available_agents": [
                "MaintenanceAgent",
                "AnalyticsAgent",
                "MLInsightAgent",
            ],
            "orchestration": "CrewAI",
            "credentials_configured": False,
            "status": "ERROR",
            "error": str(e),
        }
