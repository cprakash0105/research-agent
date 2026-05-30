import os
import logging
from pathlib import Path
from app.models import Source
from app.pii import redact_pii, scan_document

logger = logging.getLogger("research-agent.loader")

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".csv"}


def load_file(file_path: str, file_name: str, redact: bool = True) -> tuple[list[Source], dict]:
    """Load a file and return (sources, pii_report). Optionally redacts PII."""
    ext = Path(file_name).suffix.lower()
    logger.info(f"Loading file: {file_name} (type: {ext}, redact_pii={redact})")

    if ext not in SUPPORTED_EXTENSIONS:
        logger.warning(f"Unsupported file type: {ext}")
        return [], {"has_pii": False, "total_findings": 0}

    try:
        if ext == ".pdf":
            sources = _load_pdf(file_path, file_name)
        else:
            sources = _load_text(file_path, file_name)

        # PII scan and optional redaction
        pii_report = {"has_pii": False, "total_findings": 0, "entity_counts": {}}
        if sources and redact:
            for i, source in enumerate(sources):
                scan = scan_document(source.content)
                if scan["has_pii"]:
                    pii_report["has_pii"] = True
                    pii_report["total_findings"] += scan["total_findings"]
                    for entity, count in scan["entity_counts"].items():
                        pii_report["entity_counts"][entity] = pii_report["entity_counts"].get(entity, 0) + count

                    # Redact PII
                    redacted_text, _ = redact_pii(source.content)
                    sources[i] = Source(
                        title=source.title,
                        url=source.url,
                        content=redacted_text,
                        query=source.query,
                    )
                    logger.info(f"PII redacted from {file_name}")

        return sources, pii_report

    except Exception as e:
        logger.error(f"Failed to load file {file_name}: {e}", exc_info=True)
        return [], {"has_pii": False, "total_findings": 0}


def _load_text(file_path: str, file_name: str) -> list[Source]:
    """Load plain text, markdown, or CSV files."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if not content.strip():
        logger.warning(f"File {file_name} is empty")
        return []

    logger.info(f"Loaded text file: {file_name} ({len(content)} chars)")
    return [Source(
        title=file_name,
        url=f"local://{file_name}",
        content=content,
        query="user_upload",
    )]


def _load_pdf(file_path: str, file_name: str) -> list[Source]:
    """Load PDF files using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            logger.error("Neither pypdf nor PyPDF2 installed. Install with: pip install pypdf")
            return []

    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        if not text.strip():
            logger.warning(f"PDF {file_name} has no extractable text")
            return []

        logger.info(f"Loaded PDF: {file_name} ({len(reader.pages)} pages, {len(text)} chars)")
        return [Source(
            title=file_name,
            url=f"local://{file_name}",
            content=text,
            query="user_upload",
        )]
    except Exception as e:
        logger.error(f"Error reading PDF {file_name}: {e}", exc_info=True)
        return []
