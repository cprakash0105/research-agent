import pytest
from app.pii import detect_pii, redact_pii, scan_document


class TestPIIDetection:
    """Test PII detection capabilities."""

    def test_detects_email(self):
        findings = detect_pii("Contact me at john@example.com for details.")
        entity_types = [f["entity_type"] for f in findings]
        assert "EMAIL_ADDRESS" in entity_types

    def test_detects_phone_number(self):
        findings = detect_pii("Call me at 555-123-4567.")
        entity_types = [f["entity_type"] for f in findings]
        assert "PHONE_NUMBER" in entity_types

    def test_detects_person_name(self, sample_text_with_pii):
        findings = detect_pii(sample_text_with_pii)
        entity_types = [f["entity_type"] for f in findings]
        assert "PERSON" in entity_types

    def test_no_pii_in_clean_text(self, sample_text_no_pii):
        findings = detect_pii(sample_text_no_pii)
        # Should have no or very few findings
        high_confidence = [f for f in findings if f["score"] > 0.7]
        assert len(high_confidence) == 0

    def test_empty_text(self):
        findings = detect_pii("")
        assert findings == []


class TestPIIRedaction:
    """Test PII redaction."""

    def test_redacts_email(self):
        text = "Send to john@example.com please."
        redacted, findings = redact_pii(text)
        assert "john@example.com" not in redacted
        assert len(findings) > 0

    def test_redacts_phone(self):
        text = "My number is 555-123-4567."
        redacted, findings = redact_pii(text)
        assert "555-123-4567" not in redacted

    def test_preserves_non_pii_content(self, sample_text_no_pii):
        redacted, findings = redact_pii(sample_text_no_pii)
        # Core content should remain
        assert "GraphRAG" in redacted or "knowledge graphs" in redacted

    def test_empty_text_returns_unchanged(self):
        redacted, findings = redact_pii("")
        assert redacted == ""
        assert findings == []


class TestDocumentScan:
    """Test document scanning summary."""

    def test_scan_with_pii(self, sample_text_with_pii):
        report = scan_document(sample_text_with_pii)
        assert report["has_pii"] is True
        assert report["total_findings"] > 0
        assert len(report["entity_counts"]) > 0

    def test_scan_without_pii(self, sample_text_no_pii):
        report = scan_document(sample_text_no_pii)
        # Either no PII or only low-confidence false positives
        high_confidence_findings = [
            f for f in report["findings"] if f["score"] > 0.7
        ]
        assert len(high_confidence_findings) == 0
