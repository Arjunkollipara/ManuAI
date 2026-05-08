"""Maintenance agent and tools for SOP-backed guidance."""

import logging

from rag.retriever import search_maintenance_docs

logger = logging.getLogger("agents.maintenance_agent")


def create_maintenance_agent(llm):
    from crewai import Agent
    from crewai_tools import tool

    @tool("search_maintenance_manuals")
    def search_manuals_tool(query: str) -> str:
        """Search maintenance manuals and SOPs for repair procedures and technical guidance.
        Use this for any questions about maintenance procedures, repairs, or equipment handling.
        """
        try:
            result = search_maintenance_docs(query=query, k=3)
            return result.get("formatted_context", "") or "No relevant maintenance documents were found."
        except Exception as exc:
            logger.error("Maintenance search tool failed: %s", exc)
            return f"Search unavailable: {exc}"

    return Agent(
        role="Senior Maintenance Technician",
        goal="""Find accurate maintenance procedures
                and repair instructions from official
                SOPs and technical manuals""",
        backstory="""You are an expert industrial
                maintenance technician with 20 years
                of experience maintaining turbines,
                compressors, and heavy machinery.
                You always reference official SOPs
                and provide step-by-step guidance.""",
        tools=[search_manuals_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
