import os
import logging
from tavily import TavilyClient
from app.models import Source

logger = logging.getLogger("research-agent.tools")


def _get_client() -> TavilyClient:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY environment variable is not set")
    return TavilyClient(api_key=api_key)


def search_web(query: str, max_results: int = 5) -> list[Source]:
    """Search the web using Tavily and return structured sources."""
    logger.debug(f"Searching Tavily for: {query}")
    try:
        response = _get_client().search(
            query=query,
            max_results=max_results,
            include_answer=False,
            include_raw_content=False,
        )
        sources = []
        for result in response.get("results", []):
            sources.append(Source(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                query=query,
            ))
        logger.debug(f"Tavily returned {len(sources)} results for: {query[:50]}")
        return sources
    except Exception as e:
        logger.error(f"Tavily search error for '{query}': {e}", exc_info=True)
        return []
