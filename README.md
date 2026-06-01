# Research Agent 🔬

An agentic AI research assistant that autonomously plans, searches, analyzes, and synthesizes research reports from a natural language query. Supports document uploads (PDF/TXT/MD) with PII redaction, follow-up Q&A via RAG, and a full governance/security stack.

**Live Demo:** https://research-agent-489654189917.us-central1.run.app

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CHAINLIT UI (Browser)                           │
│          https://research-agent-489654189917.us-central1.run.app         │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  🔒 Login: username/password auth                                  │ │
│  │                                                                   │ │
│  │  User Input: "Research the impact of AI on drug discovery"        │ │
│  │  📎 Upload: internal_brief.pdf (PII auto-redacted)                │ │
│  │                                                                   │ │
│  │  Agent Steps (real-time):                                         │ │
│  │    ✓ Input Validation (regex + LLM prompt injection check)        │ │
│  │    ✓ Planner: Generated 4 sub-questions                           │ │
│  │    ✓ Researcher: Searched 4 queries + indexed uploads             │ │
│  │    ✓ Analyst: RAG retrieval + synthesis                           │ │
│  │    ✓ Writer: Report with citations                                │ │
│  │    ✓ Output Safety Filter (LLM-based)                             │ │
│  │                                                                   │ │
│  │  Final Report (Markdown rendered)                                 │ │
│  │  📊 Token usage: 12,450 / 100,000 (12.4%)                        │ │
│  │                                                                   │ │
│  │  💬 Follow-up Q&A (RAG-powered)                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      GOVERNANCE & SECURITY LAYER                         │
│                                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │  Auth    │ │  Rate    │ │  Input   │ │  Output  │ │   Audit    │  │
│  │ (Login) │ │ Limiter  │ │ Guard    │ │ Filter   │ │   Trail    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │  PII     │ │  Token   │ │ Session  │ │ Encrypted│ │  Logging   │  │
│  │ Redactor │ │ Budget   │ │   TTL    │ │ Secrets  │ │ (File+Std) │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     LANGGRAPH AGENT (State Machine)                      │
│                                                                         │
│  ┌──────────┐    ┌────────────┐    ┌────────────┐    ┌──────────┐     │
│  │ PLANNER  │───▶│ RESEARCHER │───▶│  ANALYST   │───▶│  WRITER  │     │
│  │          │    │            │    │ (RAG)      │    │          │     │
│  │ Break    │    │ Web search │    │ Retrieve   │    │ Synthesize│     │
│  │ query    │    │ + build    │    │ relevant   │    │ report   │     │
│  │ into sub-│    │ FAISS      │    │ chunks via │    │ with     │     │
│  │ questions│    │ index      │    │ similarity │    │ citations│     │
│  └──────────┘    └────────────┘    └────────────┘    └──────────┘     │
│                                                                         │
│  State: { query, sub_questions, sources, vector_store,                  │
│           analysis, report }                                            │
│                                                                         │
│  Token tracking on every LLM call → budget enforcement                  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
┌──────────────────┐ ┌─────────────────┐ ┌──────────────────┐
│   Tavily API     │ │  Google Gemini  │ │   FAISS (Local)  │
│   (Web Search)   │ │  (LLM)         │ │   (Vector Store) │
│                  │ │                 │ │                  │
│ Search + Extract │ │ gemini-2.5-flash│ │ RAG retrieval    │
│ Clean results    │ │ Reasoning       │ │ + dedup          │
└──────────────────┘ └─────────────────┘ └──────────────────┘
```

---

## Agent Flow (LangGraph State Machine)

```
                    START
                      │
                      ▼
               ┌─────────────┐
               │   PLANNER   │  Breaks query into 3-5 sub-questions
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │ RESEARCHER  │  Tavily search per sub-question
               │             │  + includes uploaded documents
               │             │  → Builds FAISS vector store
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │   ANALYST   │  RAG retrieval (top-k relevant chunks)
               │   (RAG)     │  Deduplicates, ranks, synthesizes
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │   WRITER    │  Structured Markdown report
               │             │  with inline citations
               └──────┬──────┘
                      │
                      ▼
                     END
                      │
                      ▼
               ┌─────────────┐
               │  FOLLOW-UP  │  User asks questions
               │    Q&A      │  → RAG retrieval from same index
               │   (RAG)     │  → LLM answers with citations
               └─────────────┘
```

---

## RAG Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAG FLOW                                  │
│                                                                  │
│  Sources (Web + Uploads)                                         │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────┐                                                │
│  │ PII Redaction │  Presidio scans + masks before embedding      │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │ Text Splitter │  RecursiveCharacterTextSplitter               │
│  │ (500 chars,   │  chunk_size=500, overlap=50                   │
│  │  50 overlap)  │                                               │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │  Embeddings  │  Google Gemini Embedding 001                   │
│  │  (3072 dim)  │                                                │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │    FAISS     │  In-memory vector store                        │
│  │    Index     │  Similarity search (L2 distance)               │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │  Retrieval   │  Top-k chunks per query                        │
│  │  + Dedup     │  Deduplicated across sub-questions             │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  Context → LLM → Analysis / Answer                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Governance & Security Features

### Request Lifecycle

```
User Request
     │
     ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Auth     │────▶│ Rate Limit  │────▶│   Input     │
│  (Login)    │     │ (10/min)    │     │ Validation  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  Prompt     │
                                        │  Injection  │
                                        │  Guard (LLM)│
                                        └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Agent     │
                                        │  Pipeline   │
                                        │ (tracked)   │
                                        └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Output    │
                                        │   Safety    │
                                        │ Filter (LLM)│
                                        └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Audit     │
                                        │   Log       │
                                        └─────────────┘
```

### Feature Details

| # | Feature | Implementation | Description |
|---|---------|---------------|-------------|
| 1 | **Encrypted Secrets** | `security.py` | Fernet encryption for API keys. Falls back to `.env` if no encrypted store exists |
| 2 | **Input Validation** | `guardrails.py` | Max 2000 chars, regex blocks known injection patterns |
| 3 | **Prompt Injection Guard** | `guardrails.py` | LLM classifies input as SAFE/UNSAFE before processing |
| 4 | **PII Detection + Redaction** | `pii.py` + `loader.py` | Presidio scans uploads for PERSON, EMAIL, PHONE, SSN, etc. Auto-redacts before embedding |
| 5 | **Session TTL** | `main.py` | 30-minute session expiry. Auto-clears vector store and state |
| 6 | **Authentication** | `main.py` | Chainlit password auth. Configurable via `.env` |
| 7 | **Audit Trail** | `audit.py` | JSONL structured events: research_start, complete, error, file_upload, guardrail_block, rate_limit |
| 8 | **Rate Limiting** | `rate_limiter.py` | Token bucket: 10 requests per 60 seconds per user |
| 9 | **Output Filtering** | `guardrails.py` | LLM checks output for harmful content, leaked prompts, fabricated citations |
| 10 | **Token Budget** | `token_tracker.py` | 100K tokens/session budget. Warns at 80%, stops at 100% |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| UI | Chainlit (dark theme, real-time agent steps, auth) |
| Agent Framework | LangGraph (state machine) |
| LLM | Google Gemini 2.5 Flash |
| Embeddings | Google Gemini Embedding 001 |
| Web Search | Tavily API |
| Vector Store | FAISS (in-memory) |
| PII Detection | Microsoft Presidio + spaCy (en_core_web_lg) |
| Encryption | Python cryptography (Fernet) |
| Document Loading | PyPDF2 (PDF), built-in (TXT, MD, CSV) |
| Logging | Python logging (console + file) |
| Audit | Structured JSONL (append-only) |
| Container | Docker (python:3.11-slim) |
| Cloud | GCP Cloud Run (serverless) |
| Secrets | GCP Secret Manager |
| CI/CD | GCP Cloud Build |
| Local K8s | Kind (for development) |

---

## Project Structure

```
research-agent/
├── app/
│   ├── __init__.py
│   ├── main.py            # Chainlit UI, auth, session management, orchestration
│   ├── agent.py           # LangGraph state machine (4 nodes + token tracking)
│   ├── rag.py             # FAISS vector store, embedding, retrieval
│   ├── tools.py           # Tavily web search
│   ├── loader.py          # File upload handler + PII redaction integration
│   ├── prompts.py         # All LLM prompts (planner, analyst, writer, QA, guards)
│   ├── models.py          # Pydantic state models
│   ├── guardrails.py      # Input validation, prompt injection, output filtering
│   ├── pii.py             # Presidio PII detection + masking
│   ├── audit.py           # Structured JSONL audit trail
│   ├── token_tracker.py   # Per-session token budget tracking
│   ├── rate_limiter.py    # In-memory token bucket rate limiter
│   └── security.py        # Encrypted secrets management
├── public/
│   ├── logo.svg           # Custom app logo
│   └── avatar.svg         # Assistant avatar
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── secret.yaml
├── .chainlit/
│   └── config.toml        # UI config (theme, logo, features)
├── cloudbuild.yaml         # GCP Cloud Build CI/CD
├── kind-config.yaml
├── Dockerfile
├── requirements.txt
├── build.bat
├── deploy.bat
├── .env.example
├── DESIGN.md
└── README.md
```

---

## Deployment

### GCP Cloud Run (Production)

The app is deployed on GCP Cloud Run as a serverless container.

```
┌─────────────────────────────────────────────────────────────────┐
│                        GCP Project                               │
│                  (hevo-data-assignment-496803)                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Cloud Run Service: research-agent                         │ │
│  │  Region: us-central1                                       │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  Container (from Artifact Registry)                  │  │ │
│  │  │  - Chainlit Server (port 8080)                       │  │ │
│  │  │  - LangGraph Agent                                   │  │ │
│  │  │  - FAISS (in-memory)                                 │  │ │
│  │  │  - Presidio PII Engine + spaCy                       │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │  Memory: 2Gi | CPU: 1 | Timeout: 300s                     │ │
│  │  Min instances: 0 (scales to zero)                         │ │
│  │  Max instances: 2                                          │ │
│  │  Session affinity: enabled (WebSocket support)             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐ │
│  │ Artifact Registry │  │  Secret Manager                      │ │
│  │ (Docker images)   │  │  - GOOGLE_API_KEY                    │ │
│  │                   │  │  - TAVILY_API_KEY                    │ │
│  │ research-agent/   │  │  - CHAINLIT_AUTH_SECRET              │ │
│  │   app:latest      │  │  - AUTH_USERNAME                     │ │
│  └──────────────────┘  │  - AUTH_PASSWORD                     │ │
│                         └──────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Cloud Build (CI/CD)                                          ││
│  │  Trigger: push to main → build → deploy                      ││
│  │  Config: cloudbuild.yaml                                      ││
│  └──────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

URL: https://research-agent-489654189917.us-central1.run.app
```

#### Deploy Steps

```bash
# 1. Set project
export PROJECT_ID=hevo-data-assignment-496803
export REGION=us-central1
gcloud config set project $PROJECT_ID

# 2. Enable APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com secretmanager.googleapis.com

# 3. Create Artifact Registry
gcloud artifacts repositories create research-agent \
  --repository-format=docker --location=$REGION

# 4. Store secrets in Secret Manager
echo -n "your_key" | gcloud secrets create GOOGLE_API_KEY --data-file=-
echo -n "your_key" | gcloud secrets create TAVILY_API_KEY --data-file=-
echo -n "your_secret" | gcloud secrets create CHAINLIT_AUTH_SECRET --data-file=-
echo -n "researcher" | gcloud secrets create AUTH_USERNAME --data-file=-
echo -n "agent123" | gcloud secrets create AUTH_PASSWORD --data-file=-

# 5. Grant Cloud Run access to secrets
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 6. Build
gcloud builds submit \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/research-agent/app:latest

# 7. Deploy
gcloud run deploy research-agent \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/research-agent/app:latest \
  --region $REGION --platform managed --port 8080 \
  --memory 2Gi --cpu 1 --timeout 300 --session-affinity \
  --min-instances 0 --max-instances 2 \
  --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest,TAVILY_API_KEY=TAVILY_API_KEY:latest,CHAINLIT_AUTH_SECRET=CHAINLIT_AUTH_SECRET:latest,AUTH_USERNAME=AUTH_USERNAME:latest,AUTH_PASSWORD=AUTH_PASSWORD:latest" \
  --allow-unauthenticated
```

#### Cost

| Resource | Cost |
|----------|------|
| Cloud Run (scales to zero) | ~$0-5/month |
| Artifact Registry | ~$0.10/month |
| Secret Manager | ~$0.06/month |
| Cloud Build | Free tier (120 min/day) |
| **Total** | **~$0-5/month** |

---

### Local Development (Kind Cluster)

```
┌─────────────────────────────────────────────┐
│            Kind Cluster (Local)              │
│                                             │
│  ┌────────────────────────────────────────┐ │
│  │  Pod: research-agent                   │ │
│  │  ┌──────────────────────────────────┐  │ │
│  │  │  Chainlit Server (port 8080)     │  │ │
│  │  │  LangGraph Agent                 │  │ │
│  │  │  FAISS (in-memory)              │  │ │
│  │  │  Presidio PII Engine            │  │ │
│  │  └──────────────────────────────────┘  │ │
│  │  Env: from K8s Secret                  │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  ┌────────────────────────────────────────┐ │
│  │  Service: NodePort 30080 → 8080        │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

## Quick Start (Local)

```bash
# 1. Clone
git clone https://github.com/cprakash0105/research-agent.git
cd research-agent

# 2. Create .env from template
cp .env.example .env
# Edit .env with your actual API keys

# 3. Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_lg

# 4. Run
python -m chainlit run app/main.py --port 8090
```

Open http://localhost:8090 — Login: `researcher` / `agent123`

---

## Usage

| Action | How |
|--------|-----|
| Research a topic | Type any research question |
| Upload documents | Click 📎 to attach PDF/TXT/MD files |
| Follow-up Q&A | Ask questions after the report (RAG-powered) |
| Check token budget | Type `token usage` |
| Start fresh | Type `new research` |

### Supported Upload Formats

| Format | Extension | PII Scanning |
|--------|-----------|-------------|
| PDF | .pdf | ✅ |
| Plain Text | .txt | ✅ |
| Markdown | .md | ✅ |
| CSV | .csv | ✅ |

---

## API Keys

| Key | Source | Cost |
|-----|--------|------|
| GOOGLE_API_KEY | [Google AI Studio](https://aistudio.google.com/apikey) | Free (15 RPM, 1M tokens/day) |
| TAVILY_API_KEY | [tavily.com](https://tavily.com) | Free (1000 searches/month) |

---

## Logging & Observability

### Application Logs (`research_agent.log`)

```
2025-05-29 16:50:01 [INFO] research-agent - GOOGLE_API_KEY loaded successfully.
2025-05-29 16:50:01 [INFO] research-agent.agent - Building research agent graph
2025-05-29 16:50:05 [INFO] research-agent.agent - [Planner] Generated 4 sub-questions
2025-05-29 16:50:12 [INFO] research-agent.agent - [Researcher] Total sources collected: 12
2025-05-29 16:50:12 [INFO] research-agent.rag - Embedding 47 chunks into FAISS
2025-05-29 16:50:13 [INFO] research-agent.tokens - [Tokens] planner: +245 in / +89 out | Total: 334/100000 (0.3%)
2025-05-29 16:50:15 [INFO] research-agent.agent - [Analyst] Analysis complete (2341 chars)
2025-05-29 16:50:18 [INFO] research-agent.agent - [Writer] Report generated (4521 chars)
2025-05-29 16:50:18 [INFO] research-agent.tokens - [Tokens] writer: +3200 in / +1800 out | Total: 8450/100000 (8.5%)
```

### Audit Trail (`audit_trail.jsonl`)

```json
{"timestamp":"2025-05-29T16:50:01Z","event_type":"RESEARCH_START","user_id":"researcher","session_id":"abc123","query":"impact of AI on drug discovery","details":{}}
{"timestamp":"2025-05-29T16:50:18Z","event_type":"RESEARCH_COMPLETE","user_id":"researcher","session_id":"abc123","query":"impact of AI on drug discovery","details":{"sources_count":12,"token_usage":{"total_tokens":8450,"budget_used_pct":8.5}}}
{"timestamp":"2025-05-29T16:51:02Z","event_type":"FILE_UPLOAD","user_id":"researcher","session_id":"abc123","query":"","details":{"filename":"report.pdf","pii_detected":true}}
{"timestamp":"2025-05-29T16:52:30Z","event_type":"GUARDRAIL_BLOCK","user_id":"researcher","session_id":"abc123","query":"ignore all previous instructions","details":{"reason":"blocked pattern detected"}}
```

---

## Troubleshooting & Known Issues

### Issues Encountered During Development

| Issue | Symptom | Root Cause | Fix |
|-------|---------|-----------|-----|
| **OOM on file upload** | App reloads/crashes when uploading PDF | Presidio + spaCy `en_core_web_lg` model (~800MB) + app exceeds 1Gi memory limit | Increase Cloud Run memory to 2Gi: `gcloud run services update research-agent --region us-central1 --memory 2Gi` |
| **429 RESOURCE_EXHAUSTED** | "You exceeded your current quota" on LLM calls | Free tier limits: `gemini-2.5-flash` = 20 RPD, `gemini-2.0-flash` = 1500 RPD | Enable billing on GCP project (uses $300 free credit). Paid tier = 2000 RPM, unlimited RPD |
| **Model NOT_FOUND** | "models/gemini-2.0-flash is no longer available to new users" | Google deprecated `gemini-2.0-flash` for new API keys | Switch to `gemini-2.5-flash` (works with billing-enabled keys) |
| **WebSocket drop on upload** | Page reloads when attaching files | Synchronous PII scanning blocks async event loop, causing Chainlit WebSocket timeout | Run file processing in thread via `cl.make_async()`, send immediate acknowledgment message |
| **Port binding error** | `[Errno 10048] address already in use` | Previous Chainlit process still holding the port | Kill process: `netstat -ano \| findstr :8090` then `taskkill /PID <pid> /F` |
| **Chainlit config outdated** | "config.toml is outdated" error on startup | Chainlit version upgrade changed config format | Delete `.chainlit/config.toml` and let Chainlit regenerate it |
| **Container fails to start on Cloud Run** | "container failed to start and listen on PORT" | `chainlit` command not on PATH in container | Use `python -m chainlit` instead of bare `chainlit` in Dockerfile entrypoint |

### Cloud Run Configuration Tips

| Setting | Recommended Value | Why |
|---------|------------------|-----|
| Memory | **2Gi** | Presidio + spaCy model requires ~800MB, plus app overhead |
| CPU | 1 | Sufficient for single-user demo |
| Timeout | 300s | Research queries can take 30-60s with multiple LLM calls |
| Session affinity | Enabled | Required for Chainlit WebSocket connections |
| Min instances | 0 | Scales to zero (saves cost) |
| Max instances | 2 | Prevents runaway costs |

### Debugging Commands

```bash
# View Cloud Run logs
gcloud run services logs read research-agent --region us-central1 --limit 50

# Check current revision status
gcloud run revisions list --service research-agent --region us-central1

# Update memory without redeploying
gcloud run services update research-agent --region us-central1 --memory 2Gi

# Check which model works with your key
python -c "from langchain_google_genai import ChatGoogleGenerativeAI; llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash', google_api_key='YOUR_KEY'); print(llm.invoke('hi').content)"
```

---

## Interview Talking Points

> "I built an agentic AI research assistant using LangGraph with a 4-node state machine — Planner, Researcher, Analyst, Writer. It uses RAG with FAISS for grounded answers and supports document uploads with automatic PII redaction via Presidio.
>
> For governance, I implemented a full security stack: Chainlit password auth, token bucket rate limiting, LLM-based prompt injection detection, input validation with regex patterns, output safety filtering, encrypted secrets management, structured JSONL audit trails, per-session token budget tracking with 80% warnings, and 30-minute session TTL with auto-cleanup.
>
> It's deployed on GCP Cloud Run with secrets in Secret Manager, CI/CD via Cloud Build, and scales to zero when idle. The architecture is designed so each governance feature is a middleware layer — they can be toggled independently without changing the core agent logic."
