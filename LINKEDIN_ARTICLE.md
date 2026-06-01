# LinkedIn Article: Building an Agentic AI Research Assistant

---

## Title Options (pick one):

1. "I Built an Agentic AI Research Assistant with Enterprise Governance — Here's What I Learned"
2. "From Zero to Production: Building a Multi-Node AI Agent with RAG, Guardrails, and Cloud Deployment"
3. "Why Agentic AI Needs Governance — And How I Built Both in One Project"

---

## Article:

### I built an AI agent that autonomously researches any topic — and I made it production-ready.

Most AI demos stop at "call an LLM and print the response." I wanted to go further — build something that thinks in steps, uses tools, retrieves grounded information, and does it all with proper security and governance.

So I built a **Research Agent**: an agentic AI assistant that plans, searches, analyzes, and writes comprehensive research reports from a single natural language query.

🔗 GitHub: https://github.com/cprakash0105/research-agent
🌐 Live: https://research-agent-489654189917.us-central1.run.app

---

### How It Works

The agent uses a **4-node state machine** built with LangGraph:

```
User Query → Planner → Researcher → Analyst → Writer → Report
```

1. **Planner** — Breaks the query into 3-5 targeted sub-questions
2. **Researcher** — Searches the web via Tavily, collects sources, builds a FAISS vector index
3. **Analyst** — Uses RAG (Retrieval-Augmented Generation) to retrieve only the most relevant chunks and synthesize findings
4. **Writer** — Produces a structured Markdown report with inline citations

After the report, users can ask **follow-up questions** — answered via RAG against the same indexed sources.

---

### What Makes It Different: The Governance Stack

Building an AI agent is easy. Making it safe for real use is the hard part.

I implemented **10 governance and security features** — all running as middleware layers that don't touch the core agent logic:

| Feature | What It Does |
|---------|-------------|
| 🔐 Authentication | Password-based login via Chainlit |
| 🚦 Rate Limiting | Token bucket: 10 requests/min per user |
| 🛡️ Input Validation | Regex pattern blocking + length limits |
| 🧠 Prompt Injection Guard | LLM classifies input as SAFE/UNSAFE before processing |
| 🔒 PII Redaction | Microsoft Presidio scans uploaded documents, auto-masks personal data before embedding |
| ⏰ Session TTL | 30-minute expiry with auto-cleanup |
| 📋 Audit Trail | Structured JSONL events (who queried what, when, which sources) |
| 🚫 Output Filtering | LLM checks responses for harmful content or fabricated citations |
| 💰 Token Budget | Per-session tracking with 80% warnings and hard stops |
| 🔑 Encrypted Secrets | Fernet encryption for API keys at rest |

---

### RAG Pipeline

Instead of dumping all search results into the LLM prompt (which wastes tokens and reduces quality), I built a proper RAG pipeline:

- Sources are chunked (500 chars, 50 overlap)
- Embedded using Google Gemini Embedding 001
- Stored in a FAISS vector index
- Retrieved via similarity search (top-k per query)
- Deduplicated across sub-questions

This means the Analyst and Writer nodes only see the most relevant information — leading to better, more focused reports.

---

### Document Upload + PII Protection

Users can upload their own documents (PDF, TXT, MD) alongside web research. Before any document enters the RAG pipeline:

1. Presidio scans for PII (names, emails, phone numbers, SSNs)
2. Detected entities are automatically redacted
3. Only the sanitized text gets embedded

This is critical for any enterprise use case where internal documents might contain sensitive information.

---

### Deployment

The app is containerized and deployed on **GCP Cloud Run**:

- Scales to zero when idle (cost: ~$0-5/month)
- Secrets stored in GCP Secret Manager
- CI/CD via Cloud Build (auto-deploys on git push)
- Session affinity enabled for WebSocket support

Locally, it also runs on a Kind (Kubernetes in Docker) cluster for development.

---

### Tech Stack

- **Agent Framework**: LangGraph (state machine)
- **LLM**: Google Gemini 2.0 Flash
- **Search**: Tavily API
- **RAG**: FAISS + Gemini Embeddings
- **PII**: Microsoft Presidio + spaCy
- **UI**: Chainlit (dark theme, real-time agent steps)
- **Cloud**: GCP Cloud Run + Secret Manager + Cloud Build
- **Testing**: pytest (76 automated tests)

---

### Key Takeaways

1. **Agentic AI is more than prompt chaining** — A proper state machine with typed state, error handling per node, and budget tracking changes the game.

2. **Governance isn't optional** — Rate limiting, PII detection, and audit trails aren't "nice to have." They're table stakes for anything beyond a demo.

3. **RAG quality > RAG quantity** — Retrieving 8 relevant chunks beats dumping 50 raw search results into a prompt.

4. **The middleware pattern works** — Every governance feature is a layer that can be toggled independently. The agent doesn't know or care about guardrails.

5. **Cloud Run is perfect for AI side projects** — Scales to zero, handles WebSockets, and costs nothing when idle.

---

### What's Next

- Firebase Auth (Google Sign-In)
- OpenTelemetry tracing across agent nodes
- GraphRAG for multi-hop reasoning
- Persistent vector store (Cloud SQL pgvector)

---

### Resources That Helped Me

If you're starting your agentic AI journey, here are some free courses and resources I'd recommend:

| Resource | Platform | What You'll Learn |
|----------|----------|------------------|
| [Building AI Agents with LangGraph](https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/) | DeepLearning.AI | LangGraph fundamentals, multi-step agents |
| [AI Agentic Design Patterns](https://www.deeplearning.ai/short-courses/ai-agentic-design-patterns-with-autogen/) | DeepLearning.AI | Reflection, tool use, planning, multi-agent patterns |
| [Building RAG Agents with LLMs](https://learn.nvidia.com/courses/course-detail?course_id=course-v1:DLI+S-FX-15+V1) | NVIDIA DLI | RAG pipelines, retrieval strategies |
| [Generative AI Fundamentals](https://cognitiveclass.ai/courses/generative-ai-foundation-models-and-platforms) | IBM CognitiveClass.ai | Foundation models, prompt engineering, AI platforms |
| [Building Generative AI Apps](https://cognitiveclass.ai/courses/building-gen-ai-powered-apps-with-python) | IBM CognitiveClass.ai | Hands-on GenAI app development with Python |
| [LangChain for LLM Application Development](https://www.deeplearning.ai/short-courses/langchain-for-llm-application-development/) | DeepLearning.AI | Chains, memory, agents with LangChain |
| [Functions, Tools and Agents with LangChain](https://www.deeplearning.ai/short-courses/functions-tools-agents-langchain/) | DeepLearning.AI | Tool calling, function agents |
| [LangGraph Documentation](https://langchain-ai.github.io/langgraph/) | LangChain | Official docs + tutorials |
| [Google Gemini API Cookbook](https://github.com/google-gemini/cookbook) | Google | Gemini examples, embeddings, function calling |

All of these are **free** and can be completed in a few hours each.

---

If you're exploring agentic AI, I'd encourage you to go beyond the basic chatbot. Build the governance layer. Deploy it. That's where the real learning happens.

💬 Happy to discuss the architecture or answer questions in the comments.

---

## Hashtags:

#AgenticAI #LangGraph #RAG #GenerativeAI #GoogleGemini #GCP #CloudRun #AIGovernance #LLM #MachineLearning #DataEngineering #Python #Kubernetes #BuildInPublic

---

## Suggested Post (shorter version for the feed):

🔬 Built an Agentic AI Research Assistant — from zero to production.

Not just another chatbot. A 4-node LangGraph agent that:
→ Plans sub-questions
→ Searches the web
→ Builds a RAG index
→ Writes cited reports

Plus a full governance stack:
🛡️ Prompt injection detection
🔒 PII redaction (Presidio)
📋 Audit trail
💰 Token budget tracking
🚦 Rate limiting

Deployed on GCP Cloud Run (scales to zero, ~$0/month).

76 automated tests. CI/CD on push.

GitHub: https://github.com/cprakash0105/research-agent
Live: https://research-agent-489654189917.us-central1.run.app

#AgenticAI #LangGraph #RAG #GCP #AIGovernance #BuildInPublic
