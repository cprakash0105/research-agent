import logging
from typing import Optional

logger = logging.getLogger("research-agent.pii")

# Lazy-load Presidio to avoid import errors if not installed
_analyzer = None
_anonymizer = None


def _init_presidio():
    """Initialize Presidio analyzer and anonymizer."""
    global _analyzer, _anonymizer
    if _analyzer is not None:
        return True

    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine

        _analyzer = AnalyzerEngine()
        _anonymizer = AnonymizerEngine()
        logger.info("Presidio PII engine initialized")
        return True
    except ImportError:
        logger.warning(
            "Presidio not installed. PII detection disabled. "
            "Install with: pip install presidio-analyzer presidio-anonymizer spacy && "
            "python -m spacy download en_core_web_lg"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Presidio: {e}", exc_info=True)
        return False


def detect_pii(text: str) -> list[dict]:
    """Detect PII entities in text. Returns list of findings."""
    if not _init_presidio():
        return []

    try:
        results = _analyzer.analyze(
            text=text,
            language="en",
            entities=[
                "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
                "CREDIT_CARD", "IBAN_CODE", "IP_ADDRESS",
                "US_SSN", "UK_NHS", "US_PASSPORT",
            ],
        )
        findings = []
        for result in results:
            findings.append({
                "entity_type": result.entity_type,
                "start": result.start,
                "end": result.end,
                "score": result.score,
                "text": text[result.start:result.end],
            })

        if findings:
            logger.info(f"PII detected: {len(findings)} entities found")
            for f in findings:
                logger.debug(f"  {f['entity_type']}: score={f['score']:.2f}")

        return findings
    except Exception as e:
        logger.error(f"PII detection failed: {e}", exc_info=True)
        return []


def redact_pii(text: str) -> tuple[str, list[dict]]:
    """Detect and redact PII from text. Returns (redacted_text, findings)."""
    if not _init_presidio():
        return text, []

    try:
        results = _analyzer.analyze(text=text, language="en")

        if not results:
            return text, []

        anonymized = _anonymizer.anonymize(text=text, analyzer_results=results)
        findings = [
            {
                "entity_type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": r.score,
            }
            for r in results
        ]

        logger.info(f"PII redacted: {len(findings)} entities masked")
        return anonymized.text, findings

    except Exception as e:
        logger.error(f"PII redaction failed: {e}", exc_info=True)
        return text, []


def scan_document(text: str) -> dict:
    """Scan a document for PII and return a summary report."""
    findings = detect_pii(text)
    entity_counts = {}
    for f in findings:
        entity_counts[f["entity_type"]] = entity_counts.get(f["entity_type"], 0) + 1

    return {
        "has_pii": len(findings) > 0,
        "total_findings": len(findings),
        "entity_counts": entity_counts,
        "findings": findings,
    }
