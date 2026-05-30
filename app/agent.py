import json
import os
import logging
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from app.models import AgentState, Source
from app.tools import search_web
from app.rag import build_vector_store, retrieve_relevant_chunks
from app.prompts import PLANNER_PROMPT, ANALYST_PROMPT, WRITER_PROMPT
from app.token_tracker import TokenTracker, extract_token_usage

logger = logging.getLogger("research-agent.agent")

# Module-level token tracker (replaced per session in main.py)
_session_tracker: TokenTracker = None


def set_token_tracker(tracker: TokenTracker):
    global _session_tracker
    _session_tracker = tracker


def get_token_tracker() -> TokenTracker:
    global _session_tracker
    if _session_tracker is None:
        _session_tracker = TokenTracker()
    return _session_tracker


def _get_llm() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.3,
    )


def planner_node(state: AgentState) -> dict:
    """Break the research query into sub-questions."""
    logger.info(f"[Planner] Breaking down query: {state['query']}")
    tracker = get_token_tracker()

    if tracker.is_over_budget():
        logger.warning("[Planner] Token budget exceeded, using query as-is")
        return {"sub_questions": [state["query"]]}

    try:
        llm = _get_llm()
        prompt = PLANNER_PROMPT.format(query=state["query"])
        response = llm.invoke(prompt)

        # Track tokens
        inp, out = extract_token_usage(response)
        tracker.record_usage("planner", inp, out)

        content = response.content.strip()

        if content.startswith("```"):
            content = content.split("```")[1].strip()
            if content.startswith("json"):
                content = content[4:].strip()

        try:
            sub_questions = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("[Planner] Failed to parse JSON, falling back to line split")
            sub_questions = [q.strip("- ").strip() for q in content.split("\n") if q.strip()]

        sub_questions = sub_questions[:5]
        logger.info(f"[Planner] Generated {len(sub_questions)} sub-questions")
        return {"sub_questions": sub_questions}

    except Exception as e:
        logger.error(f"[Planner] Error: {e}", exc_info=True)
        return {"sub_questions": [state["query"]]}


def researcher_node(state: AgentState) -> dict:
    """Search the web for each sub-question, then build vector store."""
    logger.info(f"[Researcher] Searching {len(state['sub_questions'])} sub-questions")
    all_sources = []
    for i, question in enumerate(state["sub_questions"], 1):
        logger.info(f"[Researcher] Searching ({i}/{len(state['sub_questions'])}): {question}")
        try:
            sources = search_web(question, max_results=3)
            all_sources.extend(sources)
            logger.info(f"[Researcher] Found {len(sources)} sources for: {question[:50]}")
        except Exception as e:
            logger.error(f"[Researcher] Search failed for '{question}': {e}", exc_info=True)

    logger.info(f"[Researcher] Total sources collected: {len(all_sources)}")

    # Build FAISS vector store from collected sources
    vector_store = build_vector_store(all_sources)
    logger.info("[Researcher] Vector store built for RAG retrieval")

    return {"sources": all_sources, "vector_store": vector_store}


def analyst_node(state: AgentState) -> dict:
    """Analyze sources using RAG retrieval for relevant context."""
    logger.info("[Analyst] Analyzing with RAG retrieval")
    tracker = get_token_tracker()

    if tracker.is_over_budget():
        logger.warning("[Analyst] Token budget exceeded, skipping analysis")
        return {"analysis": "Analysis skipped: token budget exceeded."}

    try:
        llm = _get_llm()
        vector_store = state.get("vector_store")

        all_chunks = []
        queries_to_search = [state["query"]] + state["sub_questions"]

        for q in queries_to_search:
            chunks = retrieve_relevant_chunks(vector_store, q, k=4)
            all_chunks.extend(chunks)

        # Deduplicate by content
        seen = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk["content"] not in seen:
                seen.add(chunk["content"])
                unique_chunks.append(chunk)

        logger.info(f"[Analyst] Retrieved {len(unique_chunks)} unique chunks via RAG")

        context = "\n\n".join(
            f"[{c['title']}]({c['url']})\n{c['content']}" for c in unique_chunks
        )

        prompt = ANALYST_PROMPT.format(
            query=state["query"],
            sub_questions="\n".join(f"- {q}" for q in state["sub_questions"]),
            context=context,
        )
        response = llm.invoke(prompt)

        # Track tokens
        inp, out = extract_token_usage(response)
        tracker.record_usage("analyst", inp, out)

        logger.info(f"[Analyst] Analysis complete ({len(response.content)} chars)")
        return {"analysis": response.content}

    except Exception as e:
        logger.error(f"[Analyst] Error: {e}", exc_info=True)
        return {"analysis": f"Analysis failed: {e}"}


def writer_node(state: AgentState) -> dict:
    """Write the final research report."""
    logger.info("[Writer] Generating final report")
    tracker = get_token_tracker()

    if tracker.is_over_budget():
        logger.warning("[Writer] Token budget exceeded")
        return {"report": "# Budget Exceeded\n\nToken budget has been exceeded. Report generation skipped."}

    try:
        llm = _get_llm()
        seen_urls = set()
        unique_sources = []
        for s in state["sources"]:
            if s.url not in seen_urls:
                seen_urls.add(s.url)
                unique_sources.append(s)

        sources_text = "\n".join(
            f"- [{s.title}]({s.url})" for s in unique_sources
        )
        prompt = WRITER_PROMPT.format(
            query=state["query"],
            analysis=state["analysis"],
            sources=sources_text,
        )
        response = llm.invoke(prompt)

        # Track tokens
        inp, out = extract_token_usage(response)
        tracker.record_usage("writer", inp, out)

        logger.info(f"[Writer] Report generated ({len(response.content)} chars)")
        return {"report": response.content}

    except Exception as e:
        logger.error(f"[Writer] Error: {e}", exc_info=True)
        return {"report": f"# Error\n\nFailed to generate report: {e}"}


def build_agent() -> StateGraph:
    """Build and compile the research agent graph."""
    logger.info("Building research agent graph")
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "analyst")
    graph.add_edge("analyst", "writer")
    graph.add_edge("writer", END)

    compiled = graph.compile()
    logger.info("Research agent graph compiled successfully")
    return compiled
