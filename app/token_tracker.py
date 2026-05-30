import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("research-agent.tokens")

# Budget: max tokens per session (input + output combined)
DEFAULT_SESSION_BUDGET = 100_000  # ~$0.01 at Gemini pricing


class TokenTracker:
    """Tracks token usage per session with budget enforcement."""

    def __init__(self, budget: int = DEFAULT_SESSION_BUDGET):
        self.budget = budget
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.calls = []
        self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def budget_remaining(self) -> int:
        return max(0, self.budget - self.total_tokens)

    @property
    def budget_used_pct(self) -> float:
        return (self.total_tokens / self.budget) * 100 if self.budget > 0 else 0

    def is_over_budget(self) -> bool:
        return self.total_tokens >= self.budget

    def record_usage(self, node_name: str, input_tokens: int = 0, output_tokens: int = 0):
        """Record token usage from an LLM call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.calls.append({
            "node": node_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(
            f"[Tokens] {node_name}: +{input_tokens} in / +{output_tokens} out | "
            f"Total: {self.total_tokens}/{self.budget} ({self.budget_used_pct:.1f}%)"
        )

        if self.budget_used_pct > 80:
            logger.warning(f"[Tokens] Budget warning: {self.budget_used_pct:.1f}% used")

    def get_summary(self) -> dict:
        """Get a summary of token usage."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "budget": self.budget,
            "budget_remaining": self.budget_remaining,
            "budget_used_pct": round(self.budget_used_pct, 1),
            "num_calls": len(self.calls),
            "calls": self.calls,
        }


def extract_token_usage(response) -> tuple[int, int]:
    """Extract token counts from a LangChain LLM response."""
    input_tokens = 0
    output_tokens = 0

    try:
        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            usage = metadata.get("usage_metadata", {})
            input_tokens = usage.get("prompt_token_count", 0) or usage.get("input_tokens", 0)
            output_tokens = usage.get("candidates_token_count", 0) or usage.get("output_tokens", 0)
    except Exception as e:
        logger.debug(f"Could not extract token usage: {e}")

    return input_tokens, output_tokens
