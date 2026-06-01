import os
import sys
import logging
import time
from dotenv import load_dotenv

load_dotenv()

# Configure logging FIRST
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "research_agent.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
    ],
    force=True,
)
logger = logging.getLogger("research-agent")

# Initialize secrets
from app.security import init_secrets
init_secrets()

# Verify env
if not os.getenv("GOOGLE_API_KEY"):
    logger.error("GOOGLE_API_KEY not found. Check .env or encrypted secrets.")
else:
    logger.info("GOOGLE_API_KEY loaded successfully.")

if not os.getenv("TAVILY_API_KEY"):
    logger.error("TAVILY_API_KEY not found. Check .env or encrypted secrets.")
else:
    logger.info("TAVILY_API_KEY loaded successfully.")

import chainlit as cl
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agent import build_agent, set_token_tracker, get_token_tracker
from app.models import AgentState
from app.rag import retrieve_relevant_chunks
from app.loader import load_file
from app.prompts import QA_PROMPT
from app.guardrails import validate_input, check_prompt_injection, check_output_safety
from app.audit import (
    log_research_start, log_research_complete, log_research_error,
    log_file_upload, log_followup_qa, log_guardrail_block, log_rate_limit,
)
from app.token_tracker import TokenTracker, extract_token_usage
from app.rate_limiter import rate_limiter

agent = build_agent()

# Session TTL: 30 minutes
SESSION_TTL_SECONDS = 1800


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Simple password authentication. Configure in .env."""
    valid_user = os.getenv("AUTH_USERNAME", "researcher")
    valid_pass = os.getenv("AUTH_PASSWORD", "agent123")

    if username == valid_user and password == valid_pass:
        logger.info(f"User authenticated: {username}")
        return cl.User(identifier=username)
    logger.warning(f"Failed login attempt: {username}")
    return None


def _get_user_id() -> str:
    """Get current user identifier."""
    user = cl.user_session.get("user")
    if user and hasattr(user, "identifier"):
        return user.identifier
    return "anonymous"


def _get_session_id() -> str:
    """Get current session ID."""
    return cl.user_session.get("id", "unknown")


def _check_session_ttl() -> bool:
    """Check if session has expired."""
    created_at = cl.user_session.get("created_at")
    if created_at and (time.time() - created_at) > SESSION_TTL_SECONDS:
        return False
    return True


@cl.on_chat_start
async def start():
    logger.info("New chat session started")
    cl.user_session.set("vector_store", None)
    cl.user_session.set("research_done", False)
    cl.user_session.set("uploaded_sources", [])
    cl.user_session.set("created_at", time.time())
    cl.user_session.set("token_tracker", TokenTracker())

    await cl.Message(
        content="🔬 **Research Agent Ready**\n\n"
        "I can research any topic using web search + RAG.\n\n"
        "**Options:**\n"
        "1. **Type a topic** — I'll search the web, analyze, and write a report\n"
        "2. **Upload files** (PDF, TXT, MD) — I'll include them in my research\n"
        "3. **Both** — Upload files first, then ask a research question\n\n"
        "After the report, ask **follow-up questions** — I'll answer using RAG.\n\n"
        "Commands: `new research` (reset) | `token usage` (check budget)\n\n"
        "🔒 *Guardrails active: input validation, PII redaction, output filtering*"
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    query = message.content
    user_id = _get_user_id()
    session_id = _get_session_id()

    # Session TTL check
    if not _check_session_ttl():
        cl.user_session.set("vector_store", None)
        cl.user_session.set("research_done", False)
        cl.user_session.set("uploaded_sources", [])
        cl.user_session.set("created_at", time.time())
        cl.user_session.set("token_tracker", TokenTracker())
        await cl.Message(content="⏰ **Session expired.** Starting fresh. Please re-submit your query.").send()
        logger.info(f"Session expired for user: {user_id}")
        return

    # Rate limiting
    if not rate_limiter.is_allowed(user_id):
        remaining_time = rate_limiter.get_reset_time(user_id)
        log_rate_limit(user_id, session_id)
        await cl.Message(
            content=f"⚠️ **Rate limit reached.** Please wait {int(remaining_time)} seconds before trying again."
        ).send()
        return

    # Handle file uploads
    if message.elements:
        await handle_uploads(message.elements, user_id, session_id)
        if not query.strip():
            return

    # Commands
    if query.strip().lower() in ("new research", "reset", "start over"):
        cl.user_session.set("vector_store", None)
        cl.user_session.set("research_done", False)
        cl.user_session.set("uploaded_sources", [])
        cl.user_session.set("token_tracker", TokenTracker())
        await cl.Message(content="🔄 **Reset!** Give me a new research topic or upload files.").send()
        logger.info(f"Session reset by user: {user_id}")
        return

    if query.strip().lower() == "token usage":
        tracker = cl.user_session.get("token_tracker")
        if tracker:
            summary = tracker.get_summary()
            await cl.Message(
                content=f"📊 **Token Usage**\n\n"
                f"- Input tokens: {summary['total_input_tokens']:,}\n"
                f"- Output tokens: {summary['total_output_tokens']:,}\n"
                f"- Total: {summary['total_tokens']:,} / {summary['budget']:,}\n"
                f"- Budget used: {summary['budget_used_pct']}%\n"
                f"- LLM calls: {summary['num_calls']}"
            ).send()
        return

    # Input validation (regex patterns)
    is_valid, error_msg = validate_input(query)
    if not is_valid:
        log_guardrail_block(user_id, session_id, query, error_msg)
        await cl.Message(content=f"⚠️ {error_msg}").send()
        return

    # Prompt injection check (LLM-based)
    is_safe, guard_msg = await check_prompt_injection(query)
    if not is_safe:
        log_guardrail_block(user_id, session_id, query, guard_msg)
        await cl.Message(content=f"🛡️ {guard_msg}").send()
        return

    # Route to follow-up or research
    vector_store = cl.user_session.get("vector_store")
    research_done = cl.user_session.get("research_done")

    if research_done and vector_store:
        await handle_followup(query, vector_store, user_id, session_id)
        return

    await run_research(query, user_id, session_id)


async def run_research(query: str, user_id: str, session_id: str):
    """Run the full research pipeline."""
    logger.info(f"Received research query: {query}")
    log_research_start(user_id, session_id, query)

    # Set token tracker for this session
    tracker = cl.user_session.get("token_tracker") or TokenTracker()
    set_token_tracker(tracker)

    try:
        uploaded_sources = cl.user_session.get("uploaded_sources") or []

        state: AgentState = {
            "query": query,
            "sub_questions": [],
            "sources": uploaded_sources.copy(),
            "vector_store": None,
            "analysis": "",
            "report": "",
        }

        # Run the full agent
        async with cl.Step(name="🧠 Planner", type="tool") as step:
            step.input = query
            result = await cl.make_async(agent.invoke)(state)
            sub_questions = result["sub_questions"]
            step.output = "**Sub-questions generated:**\n" + "\n".join(f"- {q}" for q in sub_questions)

        async with cl.Step(name="🔍 Researcher + RAG Indexing", type="tool") as step:
            sources = result["sources"]
            web_sources = [s for s in sources if not s.url.startswith("local://")]
            local_sources = [s for s in sources if s.url.startswith("local://")]
            unique_urls = set(s.url for s in web_sources)
            output_parts = [f"**Found {len(web_sources)} web sources from {len(unique_urls)} unique URLs**"]
            if local_sources:
                output_parts.append(f"📎 **Including {len(local_sources)} uploaded document(s)**")
            output_parts.append("✅ Vector store built for RAG")
            step.input = f"Searching {len(sub_questions)} sub-questions"
            step.output = "\n".join(output_parts)

        async with cl.Step(name="📊 Analyst (RAG-powered)", type="tool") as step:
            step.input = f"RAG retrieval + analysis"
            analysis_preview = result["analysis"][:500] + "..." if len(result["analysis"]) > 500 else result["analysis"]
            step.output = analysis_preview

        async with cl.Step(name="✍️ Writer", type="tool") as step:
            step.input = "Synthesizing final report"
            step.output = f"Report generated ({len(result['report'])} characters)"

        # Output safety check
        is_safe, reason = await check_output_safety(result["report"])
        if not is_safe:
            logger.warning(f"Output flagged: {reason}")
            result["report"] += f"\n\n---\n⚠️ *Note: Output flagged by safety filter: {reason}*"

        # Store session state
        cl.user_session.set("vector_store", result.get("vector_store"))
        cl.user_session.set("research_done", True)
        cl.user_session.set("token_tracker", tracker)

        # Log completion
        token_summary = tracker.get_summary()
        log_research_complete(user_id, session_id, query, len(sources), token_summary)

        await cl.Message(content=result["report"]).send()

        # Token usage footer
        await cl.Message(
            content=f"---\n💬 Ask **follow-up questions** | `new research` to reset | `token usage` to check budget\n\n"
            f"📊 *Tokens used: {token_summary['total_tokens']:,} / {token_summary['budget']:,} "
            f"({token_summary['budget_used_pct']}%)*"
        ).send()

        logger.info(f"Research complete for: {query[:50]}")

    except Exception as e:
        error_msg = f"❌ **Error during research:** {str(e)}\n\nPlease try again or rephrase your query."
        logger.error(f"Research failed for '{query}': {e}", exc_info=True)
        log_research_error(user_id, session_id, query, str(e))
        await cl.Message(content=error_msg).send()


async def handle_uploads(elements, user_id: str, session_id: str):
    """Process uploaded files with PII detection. Runs in thread to avoid blocking."""
    uploaded_sources = cl.user_session.get("uploaded_sources") or []
    new_files = []
    pii_warnings = []

    for element in elements:
        if hasattr(element, "path") and element.path:
            try:
                # Run file loading in a thread to prevent WebSocket timeout
                sources, pii_report = await cl.make_async(load_file)(
                    element.path, element.name, True
                )
                uploaded_sources.extend(sources)
                new_files.append(element.name)

                # Audit log
                log_file_upload(user_id, session_id, element.name, pii_report["has_pii"])

                if pii_report["has_pii"]:
                    pii_warnings.append(
                        f"  - **{element.name}**: {pii_report['total_findings']} PII entities detected and redacted "
                        f"({', '.join(f'{k}: {v}' for k, v in pii_report['entity_counts'].items())})"
                    )
                logger.info(f"Uploaded file processed: {element.name} (PII: {pii_report['has_pii']})")
            except Exception as e:
                logger.error(f"Failed to process upload {element.name}: {e}", exc_info=True)
                new_files.append(f"{element.name} (failed)")

    cl.user_session.set("uploaded_sources", uploaded_sources)

    if new_files:
        msg = f"📎 **Uploaded {len(new_files)} file(s):**\n" + "\n".join(f"- {f}" for f in new_files)
        if pii_warnings:
            msg += "\n\n🔒 **PII Detection:**\n" + "\n".join(pii_warnings)
            msg += "\n\n*PII has been automatically redacted before processing.*"
        msg += "\n\nThese will be included in your next research query. Go ahead and type your topic!"
        await cl.Message(content=msg).send()


async def handle_followup(question: str, vector_store, user_id: str, session_id: str):
    """Handle follow-up questions using RAG retrieval."""
    logger.info(f"Follow-up question: {question}")
    log_followup_qa(user_id, session_id, question)

    tracker = cl.user_session.get("token_tracker") or TokenTracker()
    set_token_tracker(tracker)

    try:
        async with cl.Step(name="🔎 RAG Retrieval", type="tool") as step:
            step.input = question
            chunks = retrieve_relevant_chunks(vector_store, question, k=6)
            step.output = f"Retrieved {len(chunks)} relevant chunks"

        if not chunks:
            await cl.Message(content="I couldn't find relevant information in the research sources for that question.").send()
            return

        context = "\n\n".join(
            f"[{c['title']}]({c['url']})\n{c['content']}" for c in chunks
        )

        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.3,
            max_retries=3,
        )
        prompt = QA_PROMPT.format(context=context, question=question)
        response = await cl.make_async(llm.invoke)(prompt)

        # Track tokens
        inp, out = extract_token_usage(response)
        tracker.record_usage("followup_qa", inp, out)
        cl.user_session.set("token_tracker", tracker)

        # Output safety check
        is_safe, reason = await check_output_safety(response.content)
        answer = response.content
        if not is_safe:
            answer += f"\n\n---\n⚠️ *Output flagged: {reason}*"

        await cl.Message(content=answer).send()
        logger.info(f"Follow-up answered: {question[:50]}")

    except Exception as e:
        error_msg = f"❌ **Error answering question:** {str(e)}"
        logger.error(f"Follow-up failed for '{question}': {e}", exc_info=True)
        await cl.Message(content=error_msg).send()
