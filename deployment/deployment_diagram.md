# Manufacturing Suite - Azure Deployment Architecture

## Component Diagram

```text
┌──────────────────┐
│   User/Browser   │
└────────┬─────────┘
         │ HTTPS
         ▼
┌──────────────────────────┐
│ Azure App Service        │
│ FastAPI (api.main)       │
└───┬──────────┬───────────┘
    │          │
    │          ├──────────────────────────────┐
    │          │                              │
    ▼          ▼                              ▼
┌──────────────┐   ┌────────────────────┐   ┌─────────────────────┐
│ Azure OpenAI │   │ Azure AI Search    │   │ Azure SQL Database  │
│ GPT-4o       │   │ Vector / Keyword   │   │ Production Data     │
└──────────────┘   └────────────────────┘   └─────────────────────┘
    ▲                     ▲
    │                     │
    └──────────┬──────────┘
               │
               ▼
      ┌──────────────────────┐
      │ Azure Key Vault      │
      │ Secrets + Credentials│
      └──────────────────────┘

┌──────────────────────┐
│ ChromaDB (Local Dev) │
│ data/vector_store/   │
└──────────┬───────────┘
           │ development only
           ▼
┌──────────────────────────┐
│ FastAPI Local Runtime    │
└──────────────────────────┘

┌──────────────────────┐      ┌──────────────────────────┐
│ GitHub Actions CI/CD │─────▶│ Azure App Service Deploy │
└──────────────────────┘      └──────────────────────────┘

┌──────────────────────┐
│ Power BI Dashboard   │
│ KPI / Ops Reporting  │
└──────────┬───────────┘
           │ queries curated data
           ▼
┌──────────────────────┐
│ Azure SQL Database   │
└──────────────────────┘
```

## Data Flow Description

1. Sensor ingestion flow: Ingestion clients post sensor payloads to `/ingest`; FastAPI validates and stores readings in database tables, then persists feature-ready records for prediction and reporting.
2. ML prediction flow: `/predict` uses `ml/predict.py` model singleton, computes risk score and explanation, writes prediction and alerts to database, and returns risk output to API consumers.
3. RAG document search flow: `/search/documents` queries vector retrieval; development uses ChromaDB chunks from `documents/`, production path switches to Azure AI Search client when configured.
4. Agent query flow: `/agent/query` routes questions through CrewAI orchestration; selected agents use RAG/manual lookup, analytics SQL tools, and ML explanation tools before returning unified response.

## Security Architecture

- Key Vault usage: Production secrets (OpenAI keys, SQL credentials, search keys, client secrets) should be stored in Azure Key Vault and injected into App Service configuration at runtime.
- Secret access pattern: App runtime reads environment variables only; Key Vault-backed settings are resolved by platform identity/service principal and not hardcoded in source.
- Environment variable strategy: `.env` is for local development placeholders; production values come from secure App Service settings and Key Vault references.
- Never stored in code: API keys, SQL passwords, tenant secrets, client secrets, and signed credentials are never committed to repository files or embedded in Python modules.
