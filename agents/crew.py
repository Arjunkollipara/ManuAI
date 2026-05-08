"""Crew orchestration for routing and running agent workflows."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from langchain_openai import AzureChatOpenAI

logger = logging.getLogger("agents.crew")
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "90"))


def _run_with_timeout(func, timeout_seconds: int = AGENT_TIMEOUT_SECONDS):
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func)
    try:
        return future.result(timeout=timeout_seconds)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def get_llm():
    """Initialize Azure OpenAI LLM."""
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        temperature=0.1,
    )


def check_credentials() -> bool:
    """Check if Azure OpenAI credentials are set."""
    return bool(os.getenv("AZURE_OPENAI_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"))


def route_question(question: str) -> str:
    """
    Determine which agent should handle the question.
    Returns: "maintenance", "analytics", or "ml_insight"
    """
    question_lower = question.lower()

    maintenance_keywords = [
        "how to",
        "procedure",
        "fix",
        "repair",
        "replace",
        "sop",
        "steps",
        "maintenance",
        "bearing",
        "overheating",
        "shutdown",
    ]
    analytics_keywords = [
        "why",
        "trend",
        "stats",
        "statistics",
        "performance",
        "downtime",
        "production",
        "alerts",
        "history",
        "rate",
    ]
    ml_keywords = [
        "predict",
        "risk",
        "probability",
        "model",
        "feature",
        "flagged",
        "score",
        "failure risk",
    ]

    maintenance_score = sum(1 for k in maintenance_keywords if k in question_lower)
    analytics_score = sum(1 for k in analytics_keywords if k in question_lower)
    ml_score = sum(1 for k in ml_keywords if k in question_lower)

    scores = {
        "maintenance": maintenance_score,
        "analytics": analytics_score,
        "ml_insight": ml_score,
    }
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "analytics"


def run_single_agent(question: str, agent_type: str) -> dict:
    """Run a single agent for the given question."""
    if not question or not question.strip():
        return {
            "answer": "Please ask a non-empty question.",
            "agent_used": "none",
            "status": "INVALID_INPUT",
        }
    if not check_credentials():
        return {
            "answer": "Azure OpenAI credentials not configured. Please set AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT in .env file.",
            "agent_used": "none",
            "status": "CREDENTIALS_NOT_CONFIGURED",
        }

    try:
        from crewai import Crew, Process, Task
        from agents.analytics_agent import create_analytics_agent
        from agents.maintenance_agent import create_maintenance_agent
        from agents.ml_insight_agent import create_ml_insight_agent

        llm = get_llm()
        if agent_type == "maintenance":
            agent = create_maintenance_agent(llm)
        elif agent_type == "analytics":
            agent = create_analytics_agent(llm)
        else:
            agent = create_ml_insight_agent(llm)

        task = Task(
            description=question,
            agent=agent,
            expected_output="""A clear, detailed response
                addressing the question with specific
                data or procedures where relevant.""",
        )

        crew = Crew(
            agents=[agent], tasks=[task], process=Process.sequential, verbose=True
        )
        result = _run_with_timeout(crew.kickoff)
        return {"answer": str(result), "agent_used": agent_type, "status": "SUCCESS"}
    except FuturesTimeoutError:
        logger.error("Agent execution timed out for agent_type=%s", agent_type)
        return {
            "answer": "The agent timed out while processing the request. Try a shorter question.",
            "agent_used": agent_type,
            "status": "TIMEOUT",
        }
    except Exception as e:
        logger.error("Agent error: %s", e)
        return {
            "answer": f"Agent encountered an error: {str(e)}",
            "agent_used": agent_type,
            "status": "ERROR",
        }


def run_multi_agent(question: str) -> dict:
    """
    Run multiple agents for complex questions that need both ML insight and maintenance guidance.
    Used when question involves both diagnosis and fix.
    """
    if not question or not question.strip():
        return {
            "answer": "Please ask a non-empty question.",
            "agent_used": "multi",
            "status": "INVALID_INPUT",
        }
    if not check_credentials():
        return {
            "answer": "Azure OpenAI credentials not configured. Please set AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT in .env file.",
            "agent_used": "multi",
            "status": "CREDENTIALS_NOT_CONFIGURED",
        }

    try:
        from crewai import Crew, Process, Task
        from agents.maintenance_agent import create_maintenance_agent
        from agents.ml_insight_agent import create_ml_insight_agent

        llm = get_llm()
        ml_agent = create_ml_insight_agent(llm)
        maintenance_agent = create_maintenance_agent(llm)

        task1 = Task(
            description=f"""Analyse the failure risk for
                this question: {question}
                Use your tools to get feature importance
                and explain what sensor readings are
                most concerning.""",
            agent=ml_agent,
            expected_output="""Technical analysis of
                failure risk factors and sensor readings.""",
        )
        task2 = Task(
            description=f"""Based on the ML analysis above,
                search maintenance manuals to find the
                relevant repair or inspection procedure.
                Question: {question}""",
            agent=maintenance_agent,
            expected_output="""Step by step maintenance
                procedure relevant to the identified
                failure risk.""",
        )

        crew = Crew(
            agents=[ml_agent, maintenance_agent],
            tasks=[task1, task2],
            process=Process.sequential,
            verbose=True,
        )
        result = _run_with_timeout(crew.kickoff)
        return {
            "answer": str(result),
            "agent_used": "ml_insight + maintenance",
            "status": "SUCCESS",
        }
    except FuturesTimeoutError:
        logger.error("Multi-agent execution timed out")
        return {
            "answer": "The multi-agent workflow timed out. Try a narrower question.",
            "agent_used": "multi",
            "status": "TIMEOUT",
        }
    except Exception as e:
        logger.error("Multi-agent error: %s", e)
        return {
            "answer": f"Multi-agent error: {str(e)}",
            "agent_used": "multi",
            "status": "ERROR",
        }


def process_question(question: str, context: dict = None) -> dict:
    """
    Main entry point for all agent queries.
    Routes to single or multi-agent based on question.
    """
    question = (question or "").strip()
    if not question:
        return {
            "question": "",
            "answer": "Please ask a non-empty question.",
            "agent_used": "none",
            "sources": [],
            "status": "INVALID_INPUT",
        }

    logger.info("Processing question: %s...", question[:50])

    multi_agent_keywords = [
        "what should i do",
        "how do i fix",
        "machine is flagged",
        "what caused and how",
        "diagnose and fix",
    ]
    needs_multi = any(kw in question.lower() for kw in multi_agent_keywords)

    if needs_multi:
        logger.info("Routing to multi-agent crew")
        result = run_multi_agent(question)
    else:
        agent_type = route_question(question)
        logger.info("Routing to single agent: %s", agent_type)
        result = run_single_agent(question, agent_type)

    result["question"] = question
    result["sources"] = result.get("sources", [])
    return result
