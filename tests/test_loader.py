import pytest
from app.loader import load_file, SUPPORTED_EXTENSIONS


class TestFileLoader:
    """Test document loading functionality."""

    def test_load_text_file(self, tmp_text_file):
        sources, pii_report = load_file(tmp_text_file, "test_doc.txt", redact=False)
        assert len(sources) == 1
        assert sources[0].title == "test_doc.txt"
        assert "quantum computing" in sources[0].content
        assert sources[0].url == "local://test_doc.txt"

    def test_load_pdf_file(self, tmp_pdf_file):
        sources, pii_report = load_file(tmp_pdf_file, "test_doc.pdf", redact=False)
        assert len(sources) == 1
        assert sources[0].title == "test_doc.pdf"
        assert len(sources[0].content) > 0

    def test_unsupported_extension(self, tmp_path):
        file_path = tmp_path / "test.xyz"
        file_path.write_text("content")
        sources, pii_report = load_file(str(file_path), "test.xyz", redact=False)
        assert sources == []

    def test_empty_file(self, tmp_path):
        file_path = tmp_path / "empty.txt"
        file_path.write_text("")
        sources, pii_report = load_file(str(file_path), "empty.txt", redact=False)
        assert sources == []

    def test_pii_redaction_on_load(self, tmp_path):
        content = "Contact John Smith at john@example.com or 555-123-4567."
        file_path = tmp_path / "pii_doc.txt"
        file_path.write_text(content)
        sources, pii_report = load_file(str(file_path), "pii_doc.txt", redact=True)
        assert pii_report["has_pii"] is True
        assert "john@example.com" not in sources[0].content

    def test_no_pii_report_clean(self, tmp_path):
        content = "GraphRAG combines knowledge graphs with vector retrieval."
        file_path = tmp_path / "clean_doc.txt"
        file_path.write_text(content)
        sources, pii_report = load_file(str(file_path), "clean_doc.txt", redact=True)
        assert len(sources) == 1

    def test_supported_extensions(self):
        assert ".txt" in SUPPORTED_EXTENSIONS
        assert ".md" in SUPPORTED_EXTENSIONS
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".csv" in SUPPORTED_EXTENSIONS
        assert ".exe" not in SUPPORTED_EXTENSIONS
