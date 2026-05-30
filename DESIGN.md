# Research Agent — Design Document

## Overview

An agentic AI research assistant that autonomously plans, searches, analyzes, and synthesizes research reports from a natural language query. Built with LangGraph for agent orchestration, Gemini as the LLM, Tavily for web search, and Chainlit for the UI.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CHAINLIT UI (Browser)                         │
│                      http://localhost:8080                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  User Input: "Research the impact of AI on drug discovery"   │   │
│  │                                                             │   │
│  │  Agent Steps (real-time):                                   │   │
│  │    ✓ Planner: Generated 4 sub-questions                     │   │
│  │    ✓ Researcher: Searched 4 queries, found 12 sources       │   │
│  │    ✓ Writer: Synthesized report with citations              │   │
│  │                                                             │   │
│  │  Final Report (Markdown rendered)                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LANGGRAPH AGENT (State Machine)                  │
│                                                                     │
│  ┌──────────┐    ┌────────────┐    ┌────────────┐    ┌──────────┐ │
│  │ PLANNER  │───▶│ RESEARCHER │───▶│  ANALYST   │───▶│  WRITER  │ │
│  │          │    │            │    │            │    │          │ │
│  │ Break    │    │ Search web │    │ Deduplicate│    │ Synthesize│ │
│  │ query    │    │ per sub-   │    │ Rank       │    │ report   │ │
│  │ into sub-│    │ question   │    │ sources    │    │ with     │ │
│  │ questions│    │ via Tavily │    │ Extract    │    │ citations│ │
│  │          │    │            │    │ key facts  │    │          │ │
│  └──────────┘    └────────────┘    └────────────┘    └──────────┘ │
│                                                                     │
│  State: { query, sub_questions, sources, analysis, report }         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
┌──────────────────┐ ┌─────────────────┐ ┌──────────────────┐
│   Tavily API     │ │  Google Gemini  │ │   FAISS (Local)  │
│   (Web Search)   │ │  (LLM)         │ │   (Dedup Store)  │
│                  │ │                 │ │                  │
│ Search + Extract │ │ gemini-2.0-flash│ │ Source dedup     │
│ Clean results    │ │ Reasoning       │ │ via embeddings   │
└──────────────────┘ └─────────────────┘ └──────────────────┘
```

---

## Agent State Machine (LangGraph)

```
                    START
                      │
                      ▼
               ┌─────────────┐
               │   PLANNER   │
               │             │
               │ Input: query│
               │ Output:     │
               │  sub_questions (3-5)
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │ RESEARCHER  │
               │             │
               │ For each sub_question:
               │   → Tavily search
               │   → Collect sources
               │ Output:     │
               │  sources[]  │
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │   ANALYST   │
               │             │
               │ Deduplicate │
               │ Rank by     │
               │  relevance  │
               │ Extract key │
               │  findings   │
               │ Output:     │
               │  analysis   │
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │   WRITER    │
               │             │
               │ Synthesize  │
               │ Structure   │
               │ Add citations│
               │ Output:     │
               │  report (MD)│
               └──────┬──────┘
                      │
                      ▼
                     END
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| UI | Chainlit |
| Agent Framework | LangGraph |
| LLM | Google Gemini 2.0 Flash |
| Web Search | Tavily API |
| Vector Store | FAISS (in-memory, for source dedup) |
| Embeddings | Google Gemini Embedding 001 |
| Container | Docker (python:3.11-slim) |
| Orchestration | Kubernetes (Kind) |
| Config | python-dotenv |

---

## Deployment

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
│  │  └──────────────────────────────────┘  │ │
│  │  Env: GOOGLE_API_KEY, TAVILY_API_KEY   │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  ┌────────────────────────────────────────┐ │
│  │  Service: NodePort 30080 → 8080        │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  Kind extraPortMappings: 8080 → 8080       │
└─────────────────────────────────────────────┘
```

Access: `http://localhost:8080`

---

## API Keys Required

| Key | Source | Cost |
|-----|--------|------|
| GOOGLE_API_KEY | GCP Console (Generative Language API) | $0 (free tier / $300 credit) |
| TAVILY_API_KEY | tavily.com | $0 (1000 searches/month free) |
