import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("research-agent.audit")

AUDIT_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audit_trail.jsonl")


class AuditEvent:
    """Structured audit event."""

    def __init__(
        self,
        event_type: str,
        user_id: str = "anonymous",
        session_id: str = "",
        query: str = "",
        details: Optional[dict] = None,
    ):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_type = event_type
        self.user_id = user_id
        self.session_id = session_id
        self.query = query
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "query": self.query,
            "details": self.details,
        }


def log_event(event: AuditEvent):
    """Write an audit event to the JSONL audit trail."""
    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")
        logger.debug(f"Audit event logged: {event.event_type}")
    except Exception as e:
        logger.error(f"Failed to write audit event: {e}", exc_info=True)


def log_research_start(user_id: str, session_id: str, query: str):
    """Log when a research query starts."""
    log_event(AuditEvent(
        event_type="RESEARCH_START",
        user_id=user_id,
        session_id=session_id,
        query=query,
    ))


def log_research_complete(user_id: str, session_id: str, query: str, sources_count: int, token_usage: dict):
    """Log when research completes successfully."""
    log_event(AuditEvent(
        event_type="RESEARCH_COMPLETE",
        user_id=user_id,
        session_id=session_id,
        query=query,
        details={"sources_count": sources_count, "token_usage": token_usage},
    ))


def log_research_error(user_id: str, session_id: str, query: str, error: str):
    """Log when research fails."""
    log_event(AuditEvent(
        event_type="RESEARCH_ERROR",
        user_id=user_id,
        session_id=session_id,
        query=query,
        details={"error": error},
    ))


def log_file_upload(user_id: str, session_id: str, filename: str, pii_detected: bool):
    """Log file upload events."""
    log_event(AuditEvent(
        event_type="FILE_UPLOAD",
        user_id=user_id,
        session_id=session_id,
        details={"filename": filename, "pii_detected": pii_detected},
    ))


def log_followup_qa(user_id: str, session_id: str, question: str):
    """Log follow-up Q&A events."""
    log_event(AuditEvent(
        event_type="FOLLOWUP_QA",
        user_id=user_id,
        session_id=session_id,
        query=question,
    ))


def log_guardrail_block(user_id: str, session_id: str, query: str, reason: str):
    """Log when guardrails block a request."""
    log_event(AuditEvent(
        event_type="GUARDRAIL_BLOCK",
        user_id=user_id,
        session_id=session_id,
        query=query,
        details={"reason": reason},
    ))


def log_rate_limit(user_id: str, session_id: str):
    """Log rate limit events."""
    log_event(AuditEvent(
        event_type="RATE_LIMITED",
        user_id=user_id,
        session_id=session_id,
    ))
