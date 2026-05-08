# Dependency Compatibility Report

Timestamp: 2026-05-07 01:00 IST

Final Stability Verdict: ENVIRONMENT STABLE WITH RISKS

## 1. Python Compatibility Analysis

Current local Python:

```text
env\Scripts\python.exe --version
Python 3.14.4
```

Docker Python:

```text
Dockerfile
FROM python:3.11-slim
```

Assessment:

- The project currently has a split runtime strategy: local execution uses Python 3.14.4, while Docker uses Python 3.11.
- The declared dependency set in `requirements.txt` is clearly closer to a Python 3.11 ecosystem than a Python 3.14 ecosystem.
- Python 3.14 is too new for several pinned packages in the declared requirements, especially the data/ML stack.

Evidence from failed install:

```text
env\Scripts\python.exe -m pip install -r requirements.txt
ERROR: Failed to build 'pandas' when installing build dependencies for pandas
```

Important stack trace excerpt:

```text
pandas==2.1.3 -> numpy<2,>=1.26.0
ERROR: Unknown compiler(s): [['icl'], ['cl'], ['cc'], ['gcc'], ['clang'], ['clang-cl'], ['pgcc']]
```

Interpretation:

- `pandas==2.1.3` and `numpy==1.26.2` are safe choices for Python 3.11.
- On Python 3.14, pip cannot use the declared stack cleanly and attempts source builds.
- Without local C/C++ build tooling, that install fails.

Recommendation:

- Standardize this project on Python 3.11.x for local development, Docker, CI, and Azure.
- Treat Python 3.14 as unsupported for this project until all core packages explicitly support it and the dependency graph is refreshed.

## 2. Dependency Conflict Analysis

Declared `requirements.txt` currently pins stable API, DB, data, ML, Azure, and test packages, but leaves the highest-risk ecosystem unpinned:

```text
langchain
langchain-community
langchain-openai
langchain-chroma
crewai
crewai-tools
```

That unpinned section is the main source of instability.

Installed package evidence:

```text
crewai==0.11.2
langchain==0.1.20
langchain-community==0.4.1
langchain-core==1.3.3
langchain-openai==1.2.1
langchain-chroma==1.1.0
openai==2.34.0
regex==2026.4.4
tenacity==9.1.4
numpy==2.4.4
```

`pip check` conflict evidence:

```text
crewai 0.11.2 requires instructor, which is not installed.
crewai 0.11.2 requires opentelemetry-exporter-otlp-proto-http, which is not installed.
crewai 0.11.2 has requirement langchain-openai<0.0.6,>=0.0.5, but you have langchain-openai 1.2.1.
crewai 0.11.2 has requirement openai<2.0.0,>=1.7.1, but you have openai 2.34.0.
crewai 0.11.2 has requirement regex<2024.0.0,>=2023.12.25, but you have regex 2026.4.4.
langchain 0.1.20 has requirement langchain-community<0.1,>=0.0.38, but you have langchain-community 0.4.1.
langchain 0.1.20 has requirement langchain-core<0.2.0,>=0.1.52, but you have langchain-core 1.3.3.
langchain 0.1.20 has requirement langchain-text-splitters<0.1,>=0.0.1, but you have langchain-text-splitters 1.1.2.
langchain 0.1.20 has requirement langsmith<0.2.0,>=0.1.17, but you have langsmith 0.8.1.
langchain 0.1.20 has requirement numpy<2,>=1, but you have numpy 2.4.4.
langchain 0.1.20 has requirement tenacity<9.0.0,>=8.1.0, but you have tenacity 9.1.4.
```

Root cause:

- `crewai==0.11.2` belongs to the early LangChain 0.1 generation.
- The environment contains later LangChain 1.x-family split packages.
- Those families are not compatible with each other.

## 3. Critical Dependency Risks

Critical:

- Python 3.14 cannot reliably install the declared pinned data stack.
- CrewAI 0.11.2 is incompatible with the installed OpenAI/LangChain package family.
- `requirements.txt` does not pin the packages most likely to break.

High:

- Agent execution may fail at runtime when CrewAI constructs an agent.
- RAG imports currently work, but `HuggingFaceEmbeddings` from `langchain_community.embeddings` is deprecated.
- `langchain-chroma==1.1.0` currently expects modern `chromadb>=1.3.5`, while `requirements.txt` says `chromadb>=0.4.22,<0.5.0`.

Medium:

- Pydantic v2 warning exists because model configs still use `orm_mode`.
- Azure package versions installed locally differ from the declared pins.

Low:

- `pytest` and `httpx` are newer locally than declared, but tests pass.

## 4. CrewAI/LangChain/OpenAI Compatibility Matrix

Observed installed matrix:

| Package | Installed | Compatibility |
|---|---:|---|
| crewai | 0.11.2 | Legacy CrewAI |
| crewai-tools | 0.0.1 | Legacy tools |
| langchain | 0.1.20 | Legacy core LangChain |
| langchain-community | 0.4.1 | Too new for langchain 0.1.20 |
| langchain-core | 1.3.3 | Too new for langchain 0.1.20 |
| langchain-openai | 1.2.1 | Too new for crewai 0.11.2 |
| langchain-chroma | 1.1.0 | Too new for declared chromadb constraint |
| openai | 2.34.0 | Too new for crewai 0.11.2 |
| regex | 2026.4.4 | Too new for crewai 0.11.2 |

Recommended legacy-compatible matrix for minimum code churn:

| Package | Recommended Pin | Reason |
|---|---:|---|
| crewai | 0.11.2 | Keep current agent API behavior |
| crewai-tools | 0.0.1 | Matches current import style: `from crewai_tools import tool` |
| instructor | 0.5.2 | Required by CrewAI 0.11.2 |
| langchain | 0.1.20 | Already installed and compatible with existing code style |
| langchain-community | 0.0.38 | Satisfies `langchain==0.1.20` requirement `<0.1,>=0.0.38` |
| langchain-core | 0.1.53 | Satisfies `langchain==0.1.20` requirement `<0.2,>=0.1.52` |
| langchain-openai | 0.0.5 | Explicitly required by CrewAI 0.11.2 |
| langchain-chroma | 0.1.0 | Fits early LangChain and ChromaDB 0.4 generation |
| langchain-text-splitters | 0.0.2 | Fits LangChain 0.1 generation |
| langsmith | 0.1.147 | Fits `langchain==0.1.20` requirement `<0.2,>=0.1.17` |
| openai | 1.12.0 | Satisfies CrewAI `<2.0.0,>=1.7.1` |
| regex | 2023.12.25 | Satisfies CrewAI `<2024.0.0,>=2023.12.25` |
| tenacity | 8.2.3 | Satisfies LangChain `<9.0.0,>=8.1.0` |
| chromadb | 0.4.24 | Satisfies original `chromadb>=0.4.22,<0.5.0` |

Why this matrix:

- It preserves the current application code.
- It avoids a major CrewAI migration.
- It aligns the old CrewAI package with the old LangChain package generation it declares.
- It matches the existing Docker/Python 3.11 direction.

Alternative modern matrix:

- Upgrade CrewAI, LangChain, OpenAI, ChromaDB, and possibly agent construction code together.
- This may be better long term, but it is not a safe pre-Azure stabilization move because it risks agent API changes.

## 5. Recommended Stable Versions

Critical runtime pins:

```text
python==3.11.x
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.2
sqlalchemy==2.0.23
numpy==1.26.2
pandas==2.1.3
scikit-learn==1.3.2
pyarrow==14.0.1
openpyxl==3.1.2
pytest==7.4.3
httpx==0.27.0
```

RAG and agent pins:

```text
crewai==0.11.2
crewai-tools==0.0.1
instructor==0.5.2
openai==1.12.0
langchain==0.1.20
langchain-community==0.0.38
langchain-core==0.1.53
langchain-openai==0.0.5
langchain-chroma==0.1.0
langchain-text-splitters==0.0.2
langsmith==0.1.147
chromadb==0.4.24
sentence-transformers==2.7.0
regex==2023.12.25
tenacity==8.2.3
```

Azure pins:

```text
azure-search-documents==11.4.0
azure-identity==1.15.0
azure-keyvault-secrets==4.7.0
```

## 6. Recommended Python Version

Recommended version:

```text
Python 3.11.x
```

Reasoning:

- Docker already uses Python 3.11.
- Azure App Service supports Python 3.11.
- The pinned data/ML stack is Python 3.11-friendly.
- It avoids unsupported Python 3.14 package builds.
- It gives the best chance of consistent local, CI, Docker, and Azure behavior.

Do not use Python 3.14 for this project yet.

## 7. Clean Environment Recreation Steps

Recommended Windows steps:

```powershell
# 1. Install Python 3.11 from python.org or winget.
python --version

# 2. Verify Python 3.11 is available.
py -3.11 --version

# 3. Create a new venv. Do this only after backing up/removing the old env.
py -3.11 -m venv env311

# 4. Activate it.
.\env311\Scripts\Activate.ps1

# 5. Upgrade installer tools.
python -m pip install --upgrade pip setuptools wheel

# 6. Install from the proposed lock.
python -m pip install -r reports\requirements.lock.proposed_20260507_010000.txt

# 7. Verify dependency graph.
python -m pip check

# 8. Run project validation.
python pipeline\ingest.py
python pipeline\transform.py
python pipeline\feature_engineer.py
python pipeline\validate.py
python ml\train.py
python ml\evaluate.py
python -m pytest tests -v
```

Recommended Docker alignment:

```dockerfile
FROM python:3.11-slim
```

Keep Docker on Python 3.11 unless the whole dependency graph is upgraded.

## 8. Recommended Installation Order

Use a clean Python 3.11 virtual environment.

Install order:

1. Installer tooling:

```powershell
python -m pip install --upgrade pip setuptools wheel
```

2. Numeric/data stack first:

```powershell
python -m pip install numpy==1.26.2 pandas==2.1.3 scipy==1.11.4 scikit-learn==1.3.2 pyarrow==14.0.1
```

3. API and database stack:

```powershell
python -m pip install fastapi==0.104.1 "uvicorn[standard]==0.24.0" pydantic==2.5.2 sqlalchemy==2.0.23 python-dotenv==1.0.0
```

4. Legacy-compatible LangChain/CrewAI stack:

```powershell
python -m pip install crewai==0.11.2 crewai-tools==0.0.1 instructor==0.5.2 langchain==0.1.20 langchain-community==0.0.38 langchain-core==0.1.53 langchain-openai==0.0.5 openai==1.12.0 regex==2023.12.25 tenacity==8.2.3
```

5. RAG/vector/embedding stack:

```powershell
python -m pip install langchain-chroma==0.1.0 chromadb==0.4.24 sentence-transformers==2.7.0
```

6. Azure and tests:

```powershell
python -m pip install azure-search-documents==11.4.0 azure-identity==1.15.0 azure-keyvault-secrets==4.7.0 pytest==7.4.3 httpx==0.27.0
```

7. Final verification:

```powershell
python -m pip check
python -m pytest tests -v
```

## 9. Proposed requirements.lock.txt

Generated file:

```text
reports/requirements.lock.proposed_20260507_010000.txt
```

This file is intentionally placed under `reports/` as a proposed lock artifact. It does not replace the active `requirements.txt`.

Recommended next step:

- Create a fresh Python 3.11 environment.
- Install this proposed lock.
- Run `pip check`.
- If successful, promote the lock strategy into active dependency files.

Suggested active-file strategy:

```text
requirements.in          # human-maintained top-level requirements
requirements.lock.txt    # fully resolved pin file generated/tested on Python 3.11
requirements.txt         # either top-level or lock, but not an unpinned hybrid
```

For this project, `requirements.txt` should not leave LangChain/CrewAI/OpenAI unpinned.

## 10. Remaining Risks

Risks that remain until a Python 3.11 environment is actually rebuilt:

- The proposed lock has not been installed in a clean Python 3.11 environment in this session because Python 3.11 is not currently available locally.
- Network access is blocked in the current shell environment, so pip dry-run could not contact package indexes.
- The CrewAI stack is old and may still need minor transitive adjustments once installed cleanly.
- `torch==2.3.1` can be large and may need CPU-wheel handling depending on deployment target.
- Azure App Service deployment should install from a tested lock, not the current unpinned `requirements.txt`.

Application-level risks:

- Agent execution still requires real Azure OpenAI credentials.
- Existing lazy imports prevent module import failure, but actual CrewAI execution must be tested after dependency stabilization.
- RAG works, but the embedding import path is deprecated.

## 11. Final Stability Verdict

ENVIRONMENT STABLE WITH RISKS

Reason:

- The current application can execute locally after previous patches.
- The dependency problem is understood and has a concrete Python 3.11-compatible stabilization path.
- A proposed lock file has been generated.
- However, the active local Python 3.14 environment remains conflicted, and a clean Python 3.11 rebuild has not yet been executed on this machine.
