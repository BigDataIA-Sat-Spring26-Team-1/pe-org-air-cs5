# PE Org-AI-R Platform 🚀
> **Enterprise-Grade Intelligence Engine for Private Equity AI Due Diligence**

![Next.js](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-05998b?style=for-the-badge&logo=fastapi)
![Snowflake](https://img.shields.io/badge/Snowflake-Data_Cloud-29B5E8?style=for-the-badge&logo=snowflake)
![Redis](https://img.shields.io/badge/Redis-Caching-DC382D?style=for-the-badge&logo=redis)
![Airflow](https://img.shields.io/badge/Airflow-Orchestration-017CEE?style=for-the-badge&logo=apacheairflow)
![Playwright](https://img.shields.io/badge/Playwright-Automation-2EAD33?style=for-the-badge&logo=playwright)
![Docker](https://img.shields.io/badge/Docker-Orchestration-2496ED?style=for-the-badge&logo=docker)
![Nginx](https://img.shields.io/badge/Nginx-Reverse_Proxy-009639?style=for-the-badge&logo=nginx)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6B35?style=for-the-badge)
![LiteLLM](https://img.shields.io/badge/LiteLLM-Multi--Model_Router-6B46C1?style=for-the-badge)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent_Orchestration-1C7D54?style=for-the-badge)
![MCP](https://img.shields.io/badge/MCP-Tool_Gateway-FF6600?style=for-the-badge)
![Prometheus](https://img.shields.io/badge/Prometheus-Observability-E6522C?style=for-the-badge&logo=prometheus)

The **PE Org-AI-R Platform** is a sophisticated data orchestration and analytics platform engineered to help Private Equity firms assess the technological maturity and AI readiness of target portfolio companies. The system automates the capture of high-fidelity signals from SEC filings, global patent registries, technology job markets, and **Glassdoor employee reviews** to compute a multi-dimensional AI-readiness score. **Case Study 4** extends the platform with a **Retrieval-Augmented Generation (RAG) Search Engine** — combining ChromaDB vector search, BM25 sparse retrieval, and a multi-provider LLM router (LiteLLM) to transform evidence into professional, citation-backed IC Meeting Packages. **Case Study 5** extends the platform further with a **LangGraph multi-agent due diligence workflow**, a **Model Context Protocol (MCP) server** for Claude Desktop tool integration, **Investment ROI tracking** with MOIC/AI-attribution analytics, and a **Prometheus observability layer** — all surfaced through four new Next.js dashboard pages.

---

## 🛠 Technology Stack & Core Dependencies

| Layer | Technologies & Frameworks |
| :--- | :--- |
| **Frontend** | ![Next.js](https://img.shields.io/badge/Next.js-000?style=flat&logo=next.js&logoColor=white) **Next.js 15 (App Router)**, **TypeScript**, **Tailwind CSS**, **Lucide React** |
| **Backend** | ![FastAPI](https://img.shields.io/badge/FastAPI-05998b?style=flat&logo=fastapi&logoColor=white) **FastAPI**, **Pydantic V2**, **Structured Logging (structlog)**, **Tenacity (Retry Logic)** |
| **Data & Cache** | ![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?style=flat&logo=snowflake&logoColor=white) **Snowflake (SQL Alchemy + Snowflake-connector)**, ![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white) **Redis (aioredis)** |
| **Orchestration** | ![Airflow](https://img.shields.io/badge/Airflow-017CEE?style=flat&logo=apacheairflow&logoColor=white) **Apache Airflow 2.x** (TaskFlow API, Dynamic Task Mapping) |
| **Pipelines** | ![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat&logo=playwright&logoColor=white) **Playwright (Stealth Mode)**, **JobSpy (LinkedIn Scraper)**, **Wextractor (Glassdoor API)**, **Boto3 (AWS S3)** |
| **RAG & Vector Search** | **ChromaDB** (Persistent HNSW cosine index), **text-embedding-3-small** (via LiteLLM), **BM25Okapi** (`rank-bm25`), **HyDE** query expansion |
| **LLM Routing** | **LiteLLM** (`acompletion`) — multi-model async router (GPT-4o primary, Claude-3.5-Sonnet fallback) with `$50/day` budget cap |
| **Agentic Orchestration** | **LangGraph** (StateGraph, conditional edge routing, HITL checkpoint), **python-docx** (IC Memo & LP Letter Word export) |
| **MCP Server** | **MCP SDK 1.x** (SSE transport + stdio), **mcp-remote** npm bridge for Claude Desktop connectivity |
| **Observability** | **Prometheus** (`prometheus_client`) — counters for MCP tool calls, agent invocations, HITL approvals, CS client calls |
| **Investment Analytics** | Custom MOIC / annualised-ROI / AI-attribution calculator, EV-weighted Fund-AI-R aggregator |
| **Reverse Proxy** | ![Nginx](https://img.shields.io/badge/Nginx-009639?style=flat&logo=nginx&logoColor=white) **Nginx** (unified gateway for API + Frontend + MCP + Docs) |
| **Testing** | ![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=flat&logo=pytest&logoColor=white) **Pytest**, **Asyncio In-Memory Testing** |

---

## 📚 Documentation & Resources
*   **Codelabs Guide**: [Detailed Step-by-Step Walkthrough](https://codelabs-preview.appspot.com/?file_id=1ZMZQVoVryvtwnCxgK_-nMqgqGZELZYVzpC4K1OSTRy8#6)
*   **Codelab Documentation**: [Project Technical Manual](https://docs.google.com/document/d/1ZMZQVoVryvtwnCxgK_-nMqgqGZELZYVzpC4K1OSTRy8/edit?usp=sharing)
*   **Video Demonstration**: [Full Platform Walkthrough](https://drive.google.com/file/d/1Vr77ca3YGzqyzr5XXE_Sezia3PEuSRI6/view?usp=sharing)
*   **Architecture Diagram**:
    ![Architecture Diagram](./pe-org-air-platform/Architecture_Diagram.jpeg)

---

## 📂 Project Structure
```text
.
├── pe-org-air-platform/         # Core platform implementation
│   ├── .env                    # Environment credentials
│   ├── .env.example            # Environment template
│   ├── docker/                 # Deployment infrastructure
│   │   ├── Dockerfile          # Multi-stage platform build
│   │   ├── docker-compose.yml  # Full-stack orchestration
│   │   └── nginx.conf          # Reverse proxy routing
│   ├── dags/                   # Airflow DAG definitions
  |app
  |--|routers
  |--|--|metrics.py                   # Dashboard & readiness report metrics
  |--|--|signals.py                   # External signals & Glassdoor endpoints
  |--|--|rag.py                       # RAG API Gateway (/ingest, /query, /notes/*)
  |--|--|justify.py                   # IC Meeting Package endpoint (/justify)
  |--|--|agent_ui.py                  # Agentic workflow + portfolio bridge (CS5)
  |--|--|investments.py               # Investment ROI endpoints (CS5)
  |--|--|observability.py             # Prometheus metrics-snapshot endpoint (CS5)
│   ├── app/                    # FastAPI application source
│   │   ├── config.py           # Application settings (Pydantic V2)
│   │   ├── agents/             # LangGraph multi-agent system (CS5)
│   │   │   ├── supervisor.py          # StateGraph — sequential agent routing
│   │   │   ├── state.py               # DueDiligenceState TypedDict
│   │   │   ├── sec_analyst.py         # SEC analysis agent node
│   │   │   ├── scorer.py              # Scoring agent node
│   │   │   ├── evidence_agent.py      # Evidence collection agent node
│   │   │   ├── value_creator.py       # Value creation / gap analysis agent node
│   │   │   └── bonus/
│   │   │       ├── ic_memo_generator.py   # IC Memo Word (.docx) export
│   │   │       └── lp_letter_generator.py # LP Letter Word (.docx) export
│   │   ├── mcp/                # MCP Server (CS5)
│   │   │   └── server.py              # MCP SSE server (7 tools, 2 prompts, 2 resources)
│   │   ├── database/           # SQL schemas and seed data
│   │   │   ├── schema.sql      # Core company & assessment tables
│   │   │   ├── schema_culture.sql # Glassdoor scoring schema
│   │   │   └── seed.sql        # Calibration data (Bases, Industry)
│   │   ├── models/             # Pydantic & Data Models
│   │   │   └── rag.py          # CS1–CS4 models (CS2Evidence, ScoreJustification, ICMeetingPackage)
│   │   ├── pipelines/          # Data collection & analysis logic
│   │   │   ├── integration_pipeline.py # Orchestrator
│   │   │   ├── board_analyzer.py # CS3 Board analyzer
│   │   │   └── glassdoor/      # Culture signal collector
│   │   ├── routers/            # API endpoints
│   │   ├── scoring/            # Core Readiness Engine
│   │   │   ├── calculators.py  # V^R, H^R, Synergy
│   │   │   └── position_factor.py # Screenshot-compliant logic
│   │   └── services/           # DB, Cache, Sector config
│   │       ├── llm/router.py          # Multi-provider LLM router (LiteLLM + DailyBudget)
│   │       ├── search/vector_store.py # ChromaDB vector store
│   │       ├── search/ingestion.py    # IngestionService (Snowflake → ChromaDB)
│   │       ├── retrieval/hybrid.py    # Hybrid retriever (BM25 + Dense + RRF)
│   │       ├── retrieval/hyde.py      # HyDE query expansion
│   │       ├── retrieval/dimension_mapper.py # Signal-to-Dimension mapping
│   │       ├── integration/cs1_client.py     # SDK wrapper — Company/Industry
│   │       ├── integration/cs2_client.py     # SDK wrapper — Signals/Evidence
│   │       ├── integration/cs3_client.py     # SDK wrapper — Assessments/Metrics
│   │       ├── collection/analyst_notes.py   # Analyst notes ingestion
│   │       ├── justification/generator.py    # ~150-word PE memo generator
│   │       ├── workflows/ic_prep.py          # IC Meeting Package workflow
│   │       ├── analytics/fund_air.py         # EV-weighted Fund-AI-R calculator (CS5)
│   │       ├── observability/metrics.py      # Prometheus counter/histogram definitions (CS5)
│   │       └── tracking/
│   │           ├── investment_tracker.py     # MOIC / ROI / AI-attribution calculator (CS5)
│   │           └── assessment_history.py    # Multi-session trend analysis (CS5)
│   ├── frontend/               # Next.js 15 Intelligence Dashboard (App Router)
│   │   └── src/app/
│   │       ├── mcp-server/page.tsx    # MCP connection guide, tools, prompts, test prompts (CS5)
│   │       ├── workflow/page.tsx      # Agentic workflow runner with live agent progress (CS5)
│   │       ├── investments/page.tsx   # Investment ROI dashboard — MOIC, AI attribution (CS5)
│   │       └── observability/page.tsx # Prometheus metrics viewer with auto-refresh (CS5)
   ├── tests/                  # Pytest suite (21+ modules)
   └── pyproject.toml          # Core dependencies
└── Prototyping/                # Research & Scratches
```

---

## 🚀 Deployment & Installation

### 1. Requirements & Prerequisites
*   **Docker Desktop** (with Compose V2)
*   **Snowflake Account** (With `ACCOUNTADMIN` or equivalent to create tables)
*   **OpenAI API Key** (Required for CS4 RAG — embeddings and GPT-4o completions)
*   **AWS S3 Bucket** (Optional: for unstructured filing storage)
*   **PatentsView API Key** (Optional: for innovation activity signals)
*   **Wextractor API Key** (Optional: for Glassdoor review collection)
*   **Anthropic API Key** (Optional: Claude fallback in LLM router)

### 2. Environment Setup
Configure your `.env` file in the `pe-org-air-platform` directory. This file is critical as it contains Snowflake credentials, Airflow configuration, and external API keys.

```bash
cd pe-org-air-platform
cp .env.example .env
nano .env
```

**Required Configuration:**
```bash
# === Snowflake Settings ===
SNOWFLAKE_ACCOUNT="your-org-your-account"
SNOWFLAKE_USER="your-user"
SNOWFLAKE_PASSWORD="your-password"
SNOWFLAKE_DATABASE="PE_ORGAIR"
SNOWFLAKE_SCHEMA="PUBLIC"
SNOWFLAKE_WAREHOUSE="your-warehouse"
SNOWFLAKE_ROLE="ACCOUNTADMIN"

# === Application ===
SECRET_KEY="your-secret-key"
AIRFLOW_UID=501

# === Infrastructure ===
REDIS_HOST="redis"
NEXT_PUBLIC_API_URL="http://localhost:8000"

# === External Integration (Optional) ===
AWS_ACCESS_KEY_ID="your-key"
AWS_SECRET_ACCESS_KEY="your-secret"
AWS_REGION="us-east-1"
S3_BUCKET="pe-intelligence-parsed"
PATENTSVIEW_API_KEY="your-patentsview-key"
WEXTRACTOR_API_KEY="your-wextractor-key"

# === CS4 RAG (Required for RAG features) ===
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Build and Launch
From the `pe-org-air-platform` directory, run:

```bash
docker compose --env-file .env -f docker/docker-compose.yml up --build
```

All services are accessible through **Nginx reverse proxy** on a single port:

*   **Platform (Unified Entry)**: `http://localhost` — Nginx routes to the appropriate service
*   **Interactive API Docs (Swagger)**: `http://localhost/docs`
*   **Airflow UI**: `http://localhost:8080`

> **Nginx Routing Rules:**
> | Path | Routed To |
> | :--- | :--- |
> | `/api/*` | FastAPI backend (`:8000`) |
> | `/mcp/*` | MCP SSE server (`:3001`) |
> | `/docs`, `/openapi.json` | Swagger/OpenAPI UI (`:8000`) |
> | `/*` (everything else) | Next.js frontend (`:3000`) |

### 4. Docker Services Architecture

The platform runs as a **multi-container stack** orchestrated by Docker Compose:

| Service | Image / Build | Exposed Port | Purpose |
| :--- | :--- | :--- | :--- |
| **nginx** | `nginx:latest` | `:80` | Reverse proxy — single entry point for all traffic |
| **api** | Custom (Airflow base) | Internal `:8000` | FastAPI backend with all REST endpoints |
| **frontend** | Custom (Next.js) | Internal `:3000` | Next.js 15 frontend application |
| **mcp-server** | Custom (Airflow base) | Internal `:3001` | MCP SSE server — Claude Desktop / mcp-remote tool gateway |
| **airflow-webserver** | Custom (Airflow base) | `:8080` | Airflow UI for DAG management |
| **airflow-scheduler** | Custom (Airflow base) | — | DAG scheduling & task execution |
| **airflow-triggerer** | Custom (Airflow base) | — | Deferred task triggering |
| **postgres** | `postgres:13` | — | Airflow metadata database |
| **redis** | `redis:latest` | — | Caching layer & Airflow broker |

### 5. Stopping and Cleanup

**Stop containers and remove images (Recommended):**
```bash
docker compose --env-file .env -f docker/docker-compose.yml down --rmi all
```
> **Note:** This preserves your data in `./data/` and `./logs/` directories.

**Complete cleanup (includes volumes):**
```bash
# ⚠️ WARNING: This removes Redis data, Airflow metadata, and all volumes
docker compose --env-file .env -f docker/docker-compose.yml down --rmi all --volumes
```

**Periodic maintenance (recommended weekly):**
```bash
docker system prune -a -f
docker builder prune -f
```

---

## 📡 API Reference

The platform exposes a comprehensive REST API via **FastAPI** with 16 routers. Full interactive documentation is available at **`http://localhost/docs`** (Swagger UI) and **`http://localhost/openapi.json`** (OpenAPI spec).

### Endpoint Overview

| Router | Prefix | Endpoints | Description |
| :--- | :--- | :--- | :--- |
| **Health** | `/health` | `GET /health` | Dependency health check (Snowflake, Redis, S3 status) |
| **Companies** | `/api/v1/companies` | `POST /` `GET /` `GET /{id}` `PUT /{id}` `DELETE /{id}` `GET /{id}/signals/{category}` `GET /{id}/evidence` | Full CRUD, per-company signals by category, and evidence lookup |
| **Assessments** | `/api/v1` | `POST /assessments` `GET /assessments` `GET /assessments/{id}` `PATCH /assessments/{id}/status` `POST /assessments/{id}/scores` `GET /assessments/{id}/scores` `PUT /scores/{id}` | Assessment lifecycle management with dimension scoring |
| **SEC Documents** | `/api/v1/documents` | `POST /collect` `POST /collect-airflow` `GET /` `GET /{id}` `GET /{id}/chunks` | SEC filing collection (direct + Airflow trigger), document & chunk retrieval |
| **Signals** | `/api/v1/signals` | `POST /collect/glassdoor` `GET /culture/{ticker}` `GET /culture/reviews/{ticker}` `POST /collect` `GET /` `GET /evidence` `GET /summary` `GET /details/{category}` | External intelligence collection, Glassdoor reviews & culture scores, signal browsing |
| **Evidence** | `/api/v1/evidence` | `POST /collect` `POST /backfill` `GET /stats` | Batch evidence collection, full portfolio backfill, progress stats |
| **Integration** | `/api/v1/integration` | `POST /run` `POST /run-airflow` | Deep scoring pipeline (direct execution or Airflow DAG trigger) |
| **Metrics** | `/api/v1/metrics` | `GET /industry-distribution` `GET /company-stats` `GET /signal-distribution` `GET /summary` `GET /readiness-report` | Dashboard analytics & AI readiness leaderboard |
| **Industries** | `/api/v1/industries` | `GET /` | List supported industries with risk factors |
| **Config** | `/api/v1/config` | `GET /vars` `GET /dimension-weights` | Non-sensitive platform configuration & scoring dimension weights |
| **RAG Search** | `/api/v1/rag` | `POST /ingest` `POST /query` `POST /notes/ingest` `POST /notes/batch` `GET /notes/{ticker}` `POST /index-airflow` `POST /complete-pipeline` `GET /health` | RAG evidence ingestion, hybrid search, analyst notes, and end-to-end pipeline |
| **IC Justification** | `/api/v1` | `POST /justify` `GET /justify/health` | Full IC Meeting Package with per-dimension PE memos and Buy/Hold/Pass recommendation |
| **System Testing** | `/api/v1/system` | `POST /run-tests` | Trigger the full pytest suite from the API and return results |
| **Agent UI** | `/api/v1/agent-ui` | `GET /portfolio` `GET /fund-air` `POST /trigger-due-diligence` `GET /history/{company_id}` `POST /generate-ic-memo/{company_id}` `POST /generate-lp-letter/{company_id}` `GET /mcp-tools` | Agentic workflow trigger, document export (IC Memo / LP Letter), portfolio bridge, MCP tool registry |
| **Investment ROI** | `/api/v1/investments` | `GET /portfolio-roi` `GET /{company_id}/roi` | MOIC, simple ROI %, annualised ROI %, AI-attributed value % per company |
| **Observability** | `/api/v1/observability` | `GET /metrics-snapshot` | Prometheus counter snapshot grouped by metric family (mcp_tool_calls, agent_invocations, hitl_approvals, cs_client_calls) |

### Airflow DAG Trigger Endpoints

| Endpoint | DAG Triggered | Description |
| :--- | :--- | :--- |
| `POST /api/v1/documents/collect-airflow` | `sec_filing_ingestion` | Triggers SEC filing download, parsing, and Snowflake persistence |
| `POST /api/v1/integration/run-airflow` | `integration_pipeline` | Triggers the full OrgAIR scoring pipeline per ticker via Airflow |
| `POST /api/v1/rag/index-airflow` | `pe_evidence_indexing` | Triggers nightly RAG evidence indexing into ChromaDB |

---

## 🔄 Airflow Pipeline Orchestration & Resilience

The platform leverages **Apache Airflow 2.x** with the **TaskFlow API** and **Dynamic Task Mapping** to orchestrate all data collection and scoring pipelines.

### **The Backend-Airflow Bridge (Singleton Pattern)**
Unlike traditional Airflow setups, this platform treats Airflow as a **high-scalability worker pool**:
*   **REST Trigger Mechanism**: The FastAPI backend acts as a singleton gateway. When a user creates an assessment, the backend validates the request and invokes the Airflow REST API to trigger the `integration_pipeline` DAG.
*   **Dynamic Task Mapping (`.expand()`)**: The core scoring pipeline uses dynamic mapping to process N companies in parallel. Each company is encapsulated in a `MappedTaskGroup`, ensuring isolation and concurrency.
*   **Graceful Failure**: Tasks use `TriggerRule.ALL_DONE`. If the Glassdoor scraper fails due to a rate limit, the SEC and Patent analysis still complete, allowing the system to compute a "Partial Score" with a lowered confidence interval.
*   **Shared Volume Analytics**: Heavy XCom payloads (like 10-K filing chunks) are stored in a shared Docker volume (`./data/sec_downloads`), bypassing the Airflow metadata DB to maintain peak performance.

### DAG Overview

| DAG ID | Schedule | API Trigger | Description |
| :--- | :--- | :--- | :--- |
| `integration_pipeline` | `@daily` | `POST /api/v1/integration/run-airflow` | **Core scoring pipeline** — fetches active tickers, then for each company runs parallel analysis tasks (SEC rubric, Board composition, Talent signals, Culture/Glassdoor) and computes the final OrgAIR score. |
| `sec_filing_ingestion` | `@daily` | `POST /api/v1/documents/collect-airflow` | **SEC ingestion** — downloads latest 10-K/10-Q filings per ticker from EDGAR, parses and chunks documents, stores in S3 + Snowflake. |
| `sec_backfill` | Manual | — | **SEC backfill** — manually triggered to backfill historical filings for specified tickers with configurable filing types and limits. |
| `sec_quality_monitor` | `@weekly` | — | **Data quality audit** — validates Snowflake document/chunk counts, checks S3 consistency, and flags zero-chunk documents (parsing failures). |
| `pe_evidence_indexing` | `@daily (2 AM)` | `POST /api/v1/rag/index-airflow` | **RAG indexing** — fetches unindexed CS2 evidence from Snowflake, indexes into ChromaDB + BM25, marks records as indexed to prevent re-processing. |

### Integration Pipeline Workflow
```
fetch_tickers ──► [Per Company (Dynamic Map)] ──►
                   ├── init_assessment
                   ├── analyze_sec       ─┐
                   ├── analyze_board      ├──► finalize_score
                   ├── analyze_talent     │
                   └── analyze_culture   ─┘
```

### SEC Ingestion Workflow
```
get_tickers ──► download_filings (mapped) ──► discover_filings ──► process_filing (mapped) ──► save_to_snowflake (mapped) ──► cleanup
```

---

## 🏢 Glassdoor Culture Scoring

The platform incorporates **Glassdoor employee reviews** as a cultural signal dimension for AI-readiness assessment. Reviews are collected via the **Wextractor API**, scored using a **keyword-based rubric**, and aggregated with **recency and employment-status weighting**.

### Review Collection
*   Reviews are fetched from Glassdoor for target companies (e.g., NVDA, JPM, WMT, GE, DG) using the Wextractor API.
*   Raw review JSON is **cached in S3** to avoid redundant API calls during re-runs.
*   Parsed review objects include: rating, title, pros/cons text, review date, and employment status.

### Rubric-Based Scoring
The `RubricScorer` evaluates reviews across **three culture dimensions**, each scored 1–5:

| Dimension | What It Measures | Example Positive Keywords | Example Negative Keywords |
| :--- | :--- | :--- | :--- |
| **Innovation** | Creativity & forward-thinking culture | *"cutting-edge"*, *"encourages new ideas"*, *"creative freedom"* | *"resistant to change"*, *"outdated tools"*, *"bureaucratic"* |
| **Leadership** | Quality of management vision & support | *"empowering leadership"*, *"clear vision"*, *"mentorship"* | *"micromanagement"*, *"poor communication"*, *"no direction"* |
| **Adaptability** | Organizational agility & responsiveness | *"fast-paced"*, *"embraces change"*, *"agile processes"* | *"slow decision-making"*, *"rigid structure"*, *"stagnant"* |

### Weighted Aggregation
Scores are **not simple averages** — each review is weighted by recency and employment status. The final per-dimension score is computed as a **weighted average**, and keyword evidence is stored alongside scores for audit transparency.

### Data Storage
*   Scores are persisted to Snowflake using the `schema_culture.sql` schema.
*   The `glassdoor_queries.py` module contains `MERGE INTO` statements to handle upserts and prevent duplication.

---

## 🔍 RAG Search Engine (CS4)

Case Study 4 adds a **Retrieval-Augmented Generation (RAG) layer** on top of the existing evidence collection pipelines. Evidence from SEC filings, external signals, and analyst notes is indexed into a hybrid search system and used to generate professional investment memos.

### Evidence Ingestion & Retrieval
*   `POST /api/v1/rag/ingest?ticker=NVDA` pulls SEC chunks and external signals from Snowflake, embeds them via `text-embedding-3-small`, and indexes into **ChromaDB** with full metadata. The **BM25** sparse index is updated simultaneously.
*   The `DimensionMapper` tags each document with its primary OrgAIR dimension using the CS3 Task 5.0a signal-to-dimension matrix, enabling filtered retrieval.
*   The `HybridRetriever` fuses dense (ChromaDB, weight 0.6) and sparse (BM25, weight 0.4) results using **Reciprocal Rank Fusion** — semantic for conceptual queries, keyword-exact for technical terms.
*   Optional **HyDE** (Hypothetical Document Embeddings): the LLM generates a fake ideal document to expand the query before embedding, improving zero-shot retrieval on abstract questions.

### LLM Router & Budget Control
All LLM calls route through the `ModelRouter` with task-specific model chains and a `DailyBudget` Pydantic tracker that hard-caps total spend at **$50/day** — raising `RuntimeError` if exceeded.

| Task | Primary | Fallback |
| :--- | :--- | :--- |
| `EVIDENCE_EXTRACTION` | GPT-4o | Claude-3.5-Sonnet |
| `JUSTIFICATION_GENERATION` | Claude-3.5-Sonnet | GPT-4o |
| `CHAT_RESPONSE` | Claude-3-Haiku | GPT-3.5-Turbo |

### Score Justification & IC Meeting Package
*   The `JustificationGenerator` produces **~150-word PE-style investment memos** per dimension with inline `[N]` citations and an identified gap sentence.
*   `POST /api/v1/justify` runs `ICPrepWorkflow` — retrieves evidence for all 7 dimensions concurrently, re-computes V^R / H^R / Synergy / OrgAIR, and synthesises an executive summary with **key strengths, gaps, risk factors, and a Buy / Hold / Pass recommendation** as a structured `ICMeetingPackage`.

### Analyst Notes
Manual due diligence data (interview transcripts, data room docs, DD findings) can be ingested via `POST /api/v1/rag/notes/ingest` and becomes immediately searchable alongside automated signals with a confidence weight of 0.9.

---

## 🤖 LangGraph Agentic Due Diligence (CS5)

Case Study 5 introduces a **LangGraph multi-agent orchestration layer** that automates the end-to-end due diligence workflow as a sequential state machine, replacing ad-hoc API calls with a structured, auditable agent pipeline.

### Agent Graph Architecture
The workflow is implemented as a **LangGraph `StateGraph`** with five nodes connected by conditional edges:

```
SEC Analyst ──► Scorer ──► Evidence Agent ──► Value Creator* ──► HITL Check ──► END
                                                     │
                          (* skipped in Quick mode) ─┘
```

| Agent Node | Responsibility |
| :--- | :--- |
| **SEC Analyst** | Fetches and analyses SEC filing signals for the target company |
| **Scorer** | Invokes CS3 scoring engine to compute Org-AI-R, V^R, H^R, Synergy scores |
| **Evidence Agent** | Retrieves CS2 evidence signals and generates RAG-backed dimension justifications |
| **Value Creator** | Runs gap analysis and EBITDA impact projection; produces a 100-day value creation plan |
| **HITL Check** | Pauses workflow if Org-AI-R falls below threshold (default 60); sets `approval_status = pending` for analyst review |

### Full vs Quick Assessment Modes
*   **Full** — all five nodes execute; includes Value Creator gap analysis and EBITDA projection (~60–120 s)
*   **Quick** — skips Value Creator; produces scores + evidence without value creation plan (~20–40 s)

### Document Export
*   `POST /api/v1/agent-ui/generate-ic-memo/{company_id}` — generates a Word (.docx) **IC Memo** from due diligence results
*   `POST /api/v1/agent-ui/generate-lp-letter/{company_id}` — generates a Word (.docx) **LP Letter** for limited partner updates

### Agentic Workflow UI
A dedicated frontend page (`/workflow`) allows analysts to:
1. Select a portfolio company and assessment mode (Full / Quick)
2. Watch real-time agent stage progress (animated pipeline indicator)
3. Review results — score summary, HITL status badge, gap table, value creation bullets
4. Download IC Memo and LP Letter directly from the results panel

---

## 🔌 MCP Server (CS5)

The platform exposes its full analytical toolkit as a **Model Context Protocol (MCP) server**, enabling Claude Desktop and other MCP-compatible clients to call PE due diligence tools directly in natural language.

### Transport & Connection
The MCP server runs as a dedicated Docker container on port **3001** (proxied via Nginx at `/mcp/`). Claude Desktop connects via the **mcp-remote** npm bridge (stdio → SSE):

```json
{
  "mcpServers": {
    "pe-orgair": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:3001/sse"]
    }
  }
}
```

### Tools (7)

| Tool | Description |
| :--- | :--- |
| `get_portfolio_summary` | Fetch all portfolio companies with Org-AI-R, V^R, H^R scores from CS1–CS3 |
| `calculate_org_air_score` | Calculate Org-AI-R score for a company using the CS3 scoring engine |
| `get_company_evidence` | Fetch granular evidence signals (patents, SEC filings, job signals) from CS2 |
| `generate_justification` | Generate a CS4 RAG-backed justification memo for a single dimension |
| `batch_generate_justifications` | Generate justifications for multiple dimensions **in parallel** using `asyncio.gather` — faster than calling `generate_justification` repeatedly |
| `project_ebitda_impact` | Project EBITDA uplift (base / conservative / optimistic) from Org-AI-R score delta |
| `run_gap_analysis` | Analyse gaps to a target Org-AI-R score and recommend priority interventions |

### Prompts (2)
*   **`due_diligence_assessment`** — step-by-step prompt for full company due diligence
*   **`ic_meeting_prep`** — structured IC memo generation workflow (portfolio context → scorecard → value thesis → recommendation)

### Resources (2)
*   **`orgair://parameters/v2.0`** — current scoring parameters (alpha, beta, gamma values)
*   **`orgair://sectors`** — sector baselines and dimension weight overrides

### MCP Server UI
A dedicated frontend page (`/mcp-server`) provides:
- Claude Desktop JSON config with one-click copy
- Live connection health indicator
- Tool cards with parameter schemas
- Prompt workflows with copy buttons
- 15 ready-to-use test prompts across four categories (Tool Verification, Due Diligence, Comparative, Strategic)

---

## 📈 Investment ROI & Fund-AI-R (CS5)

### Investment Tracker
The `InvestmentTracker` service calculates financial return metrics for each portfolio company, attributing value creation to AI readiness improvements:

| Metric | Formula |
| :--- | :--- |
| **MOIC** | `current_ev / entry_ev` |
| **Simple ROI %** | `(current_ev - investment_amount) / investment_amount × 100` |
| **Annualised ROI %** | `((MOIC)^(1/years) - 1) × 100` |
| **AI-Attributed Value %** | `delta_org_air × ebitda_multiplier / entry_ev × 100` |

Entry EV and investment amount are seeded from CS3 scores on first call (EV proxy = `org_air × 100` MM; investment = `entry_ev × 0.3` MM).

### Fund-AI-R Calculator
An **EV-weighted composite score** across all portfolio companies, giving higher weight to larger positions. Surfaced on the Investment ROI dashboard alongside per-company MOIC, AI attribution bar chart, and best/worst performer cards.

---

## 📊 Observability (CS5)

Prometheus counters are instrumented across all major platform subsystems and exposed via `GET /api/v1/observability/metrics-snapshot`:

| Metric Family | Labels | What It Counts |
| :--- | :--- | :--- |
| `mcp_tool_calls` | `tool_name`, `status` | Every MCP tool invocation (success / error) |
| `agent_invocations` | `agent_name`, `status` | Each LangGraph agent node execution |
| `hitl_approvals` | `reason`, `decision` | HITL checkpoint events (pending / approved) |
| `cs_client_calls` | `service`, `endpoint`, `status` | CS1–CS4 SDK client HTTP calls |

The **Observability dashboard** (`/observability`) displays these counters in grouped tables with auto-refresh (every 15 s).

---

## ⚙️ Data Pipelines & Orchestration Logic

The system utilizes a multi-stage, asynchronous pipeline architecture designed for resilience and rate-limit compliance.

### **Pipeline Execution Flow**
The `IntegrationPipeline` orchestrates collection in a specific order to optimize data dependency:
1.  **Job Market Analysis**: First pass using **JobSpy** to identify AI hiring signals. This data is cached and used to resolve technical domains in step 2.
2.  **Concurrent Collection**:
    *   **Innovation Sweep**: Parallel fetch from **PatentsView API**.
    *   **Digital Presence**: Concurrent scan of `BuiltWith` and direct site signatures using **Playwright**.
    *   **Leadership Signals**: Scanning for C-suite AI focus.
3.  **Culture Analysis**: **Glassdoor reviews** are fetched, scored via the rubric engine, and persisted with weighted aggregation.
4.  **Scoring Finalization**: All dimension signals are fed into the **OrgAIR Scoring Engine** (VR, HR, Synergy, Confidence calculators) to produce the final composite score.

### **Robustness & Anti-Blocking Strategies**
To ensure uninterrupted operation and avoid IP/Rate-limit blocking, we implemented:
*   **Adaptive Rate Limiting**: The `PatentCollector` uses a custom `AsyncRateLimiter` capped at **45 req/min** to align with PatentsView quotas.
*   **Browser Stealth**: Playwright instances utilize `playwright-stealth` and **User-Agent rotation** to bypass basic bot detection on corporate websites.
*   **Interval Spacing**: SEC and Job pipelines include `asyncio.sleep` (200ms to 2s) between requests to avoid burst-detection.
*   **Retry Mechanisms**: All critical external calls are wrapped with **Exponential Backoff** using the `Tenacity` library.

### **Asynchronous Scalability**
*   **Semaphore Throttling**: The system uses `asyncio.Semaphore(5)` to prevent overwhelming Snowflake connection pools or external APIs.
*   **Non-Blocking Parsing**: Heavy CPU tasks (like parsing 50MB SEC text filings) are delegated to a `ThreadPoolExecutor` to keep the main API event loop responsive.

---

## 📐 Key Design Decisions

### **Single Source of Truth (SSOT)**
Consolidated legacy disjointed tables into a unified `companies` schema. This allows the SEC pipeline to dynamically "anchor" discovered CIKs to existing targets, ensuring a single version of the truth for every portfolio company.

### **Singleton Database Pattern**
Implemented a thread-safe **Snowflake Singleton** manager with a persistent session pool. This reduces API latency by avoiding the heavy SSL handshake required for new Snowflake connections on every request.

### **Graceful Degradation**
Integrations like S3 and PatentsView are designed to fail gracefully. If credentials are missing, the system warns the operator via structured logs but continues to serve existing data and other active collectors.

### **Airflow-Native Task Design**
Each pipeline step is wrapped as an Airflow `@task` with `asyncio.run()` bridging, allowing reuse of the existing async codebase. Dynamic Task Mapping (`expand()`) enables per-ticker parallelism without manual DAG construction.

### **Hybrid Retrieval over Pure Dense Search (CS4)**
Pure vector search fails on exact technical terms; pure BM25 misses paraphrased concepts. The 60/40 RRF fusion of ChromaDB + BM25 captures both. LiteLLM provides a unified interface so model swaps require only routing table changes, not code rewrites.

### **LangGraph for Agentic Workflows (CS5)**
LangGraph's `StateGraph` provides deterministic, auditable agent routing with typed shared state (`DueDiligenceState`). Conditional edges enable Full/Quick mode branching without duplicating agent logic. The HITL node leverages LangGraph's interrupt mechanism for human-in-the-loop approval flows.

### **MCP SSE over HTTP (CS5)**
Running the MCP server as a separate container (not embedded in FastAPI) ensures clean separation of concerns and allows Claude Desktop to connect independently of the main API. The `mcp-remote` npm bridge handles the stdio↔SSE translation required by Claude Desktop's stdio-only MCP client.

---

## 🧪 Quality & Verification

The platform maintains a comprehensive test suite with **21 test modules** covering core logic, API integrity, service mocks, and performance benchmarks.

### Running Tests
Execute the full suite within the containerized environment:
```bash
# Run all tests
docker compose --env-file .env -f docker/docker-compose.yml exec api pytest -v -s
```

Alternatively, trigger tests directly from the API:
```bash
curl -X POST http://localhost/api/v1/system/run-tests
```

### Test Categories
| Module | Focus Area |
| :--- | :--- |
| **API Integrity** (`test_api.py`) | Validates REST endpoints, status codes, and payload validation. |
| **Business Logic** (`test_flows.py`) | End-to-end verification of the Assessment → Signal → Score lifecycle. |
| **Concurrency** (`test_concurrency.py`) | Stress tests parallel scraping tasks and semaphore throttling. |
| **Performance** (`test_performance_cache.py`) | Measures Redis hit rates and latency improvements for cached metrics. |
| **External Systems** (`test_sec_downloader.py`) | Mocks SEC/PatentsView interactions to ensure resilient parsing logic. |
| **Schema Integrity** (`test_models.py`) | Deep validation of Pydantic V2 models and data transformation rules. |
| **Scoring Properties** (`test_scoring_properties.py`) | Property-based tests for scoring engine calculators (VR, HR, Synergy, Confidence). |
| **Assessment Router** (`test_assessments_router.py`) | Assessment CRUD and status transition validation. |
| **Backfill Service** (`test_backfill_mock.py`) | Backfill service orchestration with mocked external dependencies. |
| **CS3 Calculators** (`test_cs3_calculators.py`) | Case Study 3 scoring calculator unit tests. |
| **Integration Pipeline** (`test_integration_pipeline.py`) | End-to-end integration pipeline execution tests. |
| **Redis Mocks** (`test_redis_mock.py`) | Redis caching behavior with mocked Redis client. |
| **Router Coverage** (`test_router_coverage.py`) | Comprehensive coverage across all API routers. |
| **Rubric Scoring** (`test_rubrics.py`) | Glassdoor rubric scorer keyword matching and dimension scoring. |
| **S3 Storage** (`test_s3_mock.py`) | S3 storage operations with mocked AWS client. |
| **Snowflake** (`test_snowflake_mock.py`) | Snowflake database operations with mocked connections. |
| **Coverage Expansion** (`test_coverage_expansion.py`) | General coverage expansion for edge cases. |
| **RAG Search** (`test_rag_search.py`) | Vector store indexing, dense/sparse search, metadata filtering, RRF fusion logic. |
| **Dimension Mapper** (`test_dimension_mapper.py`) | Signal-to-dimension mapping correctness, source-type overrides, fallback behaviour. |
| **Justification** (`test_justify.py`) | LLM prompt construction, `ScoreJustification` model population, confidence intervals. |
| **SDK Clients** (`test_sdk_clients.py`) | CS1/CS2/CS3 client HTTP interactions, parameter serialisation, error handling. |

### Continuous Validation
The test suite is designed to be run as part of a CI/CD pipeline, ensuring that changes to the `IntegrationPipeline` do not regress scoring accuracy or rate-limit compliance.

---

## ⚠️ Known Limitations

1.  **Snowflake Constraints**: Unique constraints are metadata-only in Snowflake; duplication is prevented via `MERGE INTO` logic in our DAO layer.
2.  **BuiltWith Rendering**: Certain high-security sites may occasionally block the Playwright scan; the system falls back to job description keyword analysis in these scenarios.
3.  **Glassdoor API Quotas**: The Wextractor API has rate limits; reviews are cached in S3 to minimize redundant calls during pipeline re-runs.
4.  **BM25 is In-Memory**: The sparse index is not persisted across container restarts — re-run `/api/v1/rag/ingest` after a restart to restore the full hybrid index.
5.  **ChromaDB Volume**: Running `docker compose down --volumes` erases all indexed evidence and will require re-ingestion.
6.  **IC Package Prerequisites**: `POST /api/v1/justify` requires evidence to be ingested first via `POST /api/v1/rag/ingest`; returns `400` otherwise.
7.  **Prometheus Metrics are Process-Local**: Counters reset on container restart. The observability dashboard reflects activity since last container start, not historical totals.
8.  **MCP Sequential Tool Calls**: Claude Desktop calls MCP tools one at a time by design. Use `batch_generate_justifications` to parallelise dimension queries server-side.

---

## 👥 Team & Contributions

| Member | CS5 Contributions |
| :--- | :--- |
| **Aakash** | Advanced Hybrid RAG re-ranking (Task 8.1), History Tracking Service for multi-session trend analysis (Task 9.4), Agentic UI Bridge FastAPI router (Task 9.5), Next.js Portfolio Dashboard with live backend integration (Task 9.6), EV-weighted Fund-AI-R Calculator (Task 10.5) |
| **Rahul** | LangGraph Core Routing StateGraph & orchestrator (Task 9.1), Shared Thread Context for autonomous state persistence (Task 10.1), Supervisor Agent quality control & conditional routing logic (Task 10.3) |
| **Abhinav** | MCP Integration Gateway for LLM tool-calling (Task 9.2), Specialized Agents — Talent, Governance, Security in LangGraph (Task 9.3), IC Presentation Agent for final narrative synthesis & Word export (Task 10.2) |
