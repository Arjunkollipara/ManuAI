# Manufacturing Quality & Productivity Suite Context

## Purpose
This project aims to provide an end-to-end suite for manufacturing quality and productivity, integrating machine learning, retrieval-augmented generation (RAG), and AI agents to monitor, analyze, and optimize manufacturing processes.

## Technology Stack
- **API**: FastAPI, Uvicorn, Pydantic
- **Data & ML**: Pandas, Scikit-learn, PyArrow, OpenPyXL
- **Database**: SQLAlchemy
- **Vector DB**: ChromaDB
- **LLM/Agents**: LangChain, CrewAI
- **Testing**: Pytest

## Phase Tracker
- [x] Phase 1: Project Initialization & Skeleton
- [ ] Phase 2: Core Data Pipelines
- [ ] Phase 3: ML Models
- [ ] Phase 4: API Routes & Integration
- [ ] Phase 5: AI Agents & RAG
- [ ] Phase 6: Testing & Deployment


KNOWN ISSUES:
- crewai 0.11.2 has dependency issues on Python 3.14
  workarounds applied, document specifics
- langchain-chroma replaces langchain-community Chroma
- chromadb 1.5.x compatibility fix in vector_store.py