# Research Agent 🔬

An agentic AI research assistant that autonomously plans, searches, analyzes, and synthesizes research reports from a natural language query. Supports document uploads (PDF/TXT/MD) with PII redaction, follow-up Q&A via RAG, and a full governance/security stack.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CHAINLIT UI (Browser)                           │
│                        http://localhost:8090                             │
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
| Orchestration | Kubernetes (Kind) |
| Config | python-dotenv |

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
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── secret.yaml
├── test_docs/             # Sample docs for testing uploads
├── .chainlit/
│   └── config.toml        # Auto-generated UI config
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

## Prerequisites

- Python 3.11+
- Docker Desktop (for Kind deployment)
- Kind (`choco install kind`)
- kubectl

---

## Quick Start (Local)

```bash
# 1. Navigate to project
cd research-agent

# 2. Create .env from template
copy .env.example .env
# Edit .env with your actual API keys

# 3. Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_lg

# 4. Run
python -m chainlit run app/main.py --port 8090
```

Open http://localhost:8090

Login: `researcher` / `agent123` (configurable in `.env`)

---

## Quick Start (Kind Cluster)

```bash
# 1. Base64-encode your keys and update k8s/secret.yaml
# PowerShell:
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your_key"))

# 2. Deploy everything
deploy.bat
```

Open http://localhost:8080

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

## Configuration (.env)

```env
# API Keys
GOOGLE_API_KEY=your_key
TAVILY_API_KEY=your_key

# Authentication
AUTH_USERNAME=researcher
AUTH_PASSWORD=agent123

# Session
SESSION_TTL_SECONDS=1800
```

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

## Deployment (Kind)

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
│                                             │
│  Kind extraPortMappings: 8080 → 8080       │
└─────────────────────────────────────────────┘
```

---

## Interview Talking Points

> "I built an agentic AI research assistant using LangGraph with a 4-node state machine — Planner, Researcher, Analyst, Writer. It uses RAG with FAISS for grounded answers and supports document uploads with automatic PII redaction via Presidio.
>
> For governance, I implemented a full security stack: Chainlit password auth, token bucket rate limiting, LLM-based prompt injection detection, input validation with regex patterns, output safety filtering, encrypted secrets management, structured JSONL audit trails, per-session token budget tracking with 80% warnings, and 30-minute session TTL with auto-cleanup.
>
> The architecture is designed so each governance feature is a middleware layer — they can be toggled independently without changing the core agent logic."
