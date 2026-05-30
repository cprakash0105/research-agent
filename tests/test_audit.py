import os
import json
import pytest
from app.audit import (
    AuditEvent, log_event, log_research_start, log_research_complete,
    log_guardrail_block, log_file_upload, log_rate_limit, AUDIT_LOG_FILE,
)


@pytest.fixture(autouse=True)
def clean_audit_log():
    """Remove audit log before and after each test."""
    if os.path.exists(AUDIT_LOG_FILE):
        os.remove(AUDIT_LOG_FILE)
    yield
    if os.path.exists(AUDIT_LOG_FILE):
        os.remove(AUDIT_LOG_FILE)


class TestAuditEvent:
    """Test audit event creation."""

    def test_event_has_timestamp(self):
        event = AuditEvent(event_type="TEST", user_id="user1")
        assert event.timestamp is not None
        assert "T" in event.timestamp  # ISO format

    def test_event_to_dict(self):
        event = AuditEvent(
            event_type="RESEARCH_START",
            user_id="researcher",
            session_id="sess123",
            query="test query",
            details={"key": "value"},
        )
        d = event.to_dict()
        assert d["event_type"] == "RESEARCH_START"
        assert d["user_id"] == "researcher"
        assert d["session_id"] == "sess123"
        assert d["query"] == "test query"
        assert d["details"] == {"key": "value"}


class TestAuditLogging:
    """Test audit log writing."""

    def test_log_event_creates_file(self):
        event = AuditEvent(event_type="TEST")
        log_event(event)
        assert os.path.exists(AUDIT_LOG_FILE)

    def test_log_event_writes_json(self):
        event = AuditEvent(event_type="TEST", user_id="user1")
        log_event(event)
        with open(AUDIT_LOG_FILE, "r") as f:
            line = f.readline()
        data = json.loads(line)
        assert data["event_type"] == "TEST"
        assert data["user_id"] == "user1"

    def test_multiple_events_append(self):
        log_research_start("user1", "sess1", "query1")
        log_research_start("user2", "sess2", "query2")
        with open(AUDIT_LOG_FILE, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_log_research_complete(self):
        log_research_complete("user1", "sess1", "query", 5, {"total_tokens": 1000})
        with open(AUDIT_LOG_FILE, "r") as f:
            data = json.loads(f.readline())
        assert data["event_type"] == "RESEARCH_COMPLETE"
        assert data["details"]["sources_count"] == 5

    def test_log_guardrail_block(self):
        log_guardrail_block("user1", "sess1", "bad query", "injection detected")
        with open(AUDIT_LOG_FILE, "r") as f:
            data = json.loads(f.readline())
        assert data["event_type"] == "GUARDRAIL_BLOCK"
        assert data["details"]["reason"] == "injection detected"

    def test_log_file_upload(self):
        log_file_upload("user1", "sess1", "report.pdf", True)
        with open(AUDIT_LOG_FILE, "r") as f:
            data = json.loads(f.readline())
        assert data["event_type"] == "FILE_UPLOAD"
        assert data["details"]["filename"] == "report.pdf"
        assert data["details"]["pii_detected"] is True

    def test_log_rate_limit(self):
        log_rate_limit("user1", "sess1")
        with open(AUDIT_LOG_FILE, "r") as f:
            data = json.loads(f.readline())
        assert data["event_type"] == "RATE_LIMITED"
