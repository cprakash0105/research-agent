import os
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from app.loader import load_file
from app.models import Source


class TestFileUploadProcessing:
    """Test file upload processing logic (sync part)."""

    def test_text_file_upload(self, tmp_path):
        content = "Research on quantum computing applications in finance and trading."
        file_path = tmp_path / "research.txt"
        file_path.write_text(content)

        sources, pii_report = load_file(str(file_path), "research.txt", redact=True)
        assert len(sources) == 1
        assert sources[0].title == "research.txt"
        assert "quantum computing" in sources[0].content
        assert sources[0].url == "local://research.txt"
        assert sources[0].query == "user_upload"

    def test_markdown_file_upload(self, tmp_path):
        content = "# GraphRAG\n\nGraphRAG combines knowledge graphs with RAG pipelines."
        file_path = tmp_path / "notes.md"
        file_path.write_text(content)

        sources, pii_report = load_file(str(file_path), "notes.md", redact=True)
        assert len(sources) == 1
        assert "GraphRAG" in sources[0].content

    def test_csv_file_upload(self, tmp_path):
        content = "name,score\nmodel_a,0.95\nmodel_b,0.87\n"
        file_path = tmp_path / "results.csv"
        file_path.write_text(content)

        sources, pii_report = load_file(str(file_path), "results.csv", redact=True)
        assert len(sources) == 1
        assert "model_a" in sources[0].content

    def test_pdf_file_upload(self, tmp_pdf_file):
        sources, pii_report = load_file(tmp_pdf_file, "test.pdf", redact=True)
        assert len(sources) == 1
        assert sources[0].title == "test.pdf"
        assert len(sources[0].content) > 0

    def test_upload_with_pii_redaction(self, tmp_path):
        content = "Contact John Smith at john.smith@example.com or call 555-123-4567."
        file_path = tmp_path / "contacts.txt"
        file_path.write_text(content)

        sources, pii_report = load_file(str(file_path), "contacts.txt", redact=True)
        assert pii_report["has_pii"] is True
        assert pii_report["total_findings"] > 0
        # PII should be redacted
        assert "john.smith@example.com" not in sources[0].content
        assert "555-123-4567" not in sources[0].content

    def test_upload_without_pii_redaction(self, tmp_path):
        content = "Contact John Smith at john.smith@example.com."
        file_path = tmp_path / "contacts.txt"
        file_path.write_text(content)

        sources, pii_report = load_file(str(file_path), "contacts.txt", redact=False)
        # PII should remain when redact=False
        assert "john.smith@example.com" in sources[0].content

    def test_upload_empty_file(self, tmp_path):
        file_path = tmp_path / "empty.txt"
        file_path.write_text("")

        sources, pii_report = load_file(str(file_path), "empty.txt", redact=True)
        assert sources == []
        assert pii_report["has_pii"] is False

    def test_upload_unsupported_format(self, tmp_path):
        file_path = tmp_path / "data.xlsx"
        file_path.write_bytes(b"fake excel content")

        sources, pii_report = load_file(str(file_path), "data.xlsx", redact=True)
        assert sources == []

    def test_upload_nonexistent_file(self):
        sources, pii_report = load_file("/nonexistent/path.txt", "path.txt", redact=True)
        assert sources == []

    def test_upload_large_text_file(self, tmp_path):
        # Simulate a large document
        content = "This is a paragraph about AI research. " * 500
        file_path = tmp_path / "large_doc.txt"
        file_path.write_text(content)

        sources, pii_report = load_file(str(file_path), "large_doc.txt", redact=True)
        assert len(sources) == 1
        assert len(sources[0].content) > 1000

    def test_upload_file_with_special_characters(self, tmp_path):
        content = "Résumé: François works at Zürich office. Cost: €500."
        file_path = tmp_path / "special.txt"
        file_path.write_text(content, encoding="utf-8")

        sources, pii_report = load_file(str(file_path), "special.txt", redact=True)
        assert len(sources) == 1

    def test_multiple_files_upload(self, tmp_path):
        """Test that multiple files can be processed sequentially."""
        files = [
            ("doc1.txt", "First document about machine learning."),
            ("doc2.txt", "Second document about data engineering."),
            ("doc3.md", "# Third\n\nDocument about cloud computing."),
        ]
        all_sources = []
        for name, content in files:
            file_path = tmp_path / name
            file_path.write_text(content)
            sources, _ = load_file(str(file_path), name, redact=True)
            all_sources.extend(sources)

        assert len(all_sources) == 3
        assert all_sources[0].title == "doc1.txt"
        assert all_sources[1].title == "doc2.txt"
        assert all_sources[2].title == "doc3.md"


class TestFileUploadAsync:
    """Test that file upload can run in a thread without blocking."""

    def test_load_file_is_thread_safe(self, tmp_path):
        """Verify load_file can be called from a thread pool."""
        import concurrent.futures

        content = "Thread-safe test content about neural networks."
        file_path = tmp_path / "thread_test.txt"
        file_path.write_text(content)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(load_file, str(file_path), "thread_test.txt", True)
            sources, pii_report = future.result(timeout=30)

        assert len(sources) == 1
        assert "neural networks" in sources[0].content

    def test_concurrent_file_uploads(self, tmp_path):
        """Verify multiple files can be processed concurrently."""
        import concurrent.futures

        files = []
        for i in range(5):
            file_path = tmp_path / f"concurrent_{i}.txt"
            file_path.write_text(f"Document {i} about topic {i}.")
            files.append((str(file_path), f"concurrent_{i}.txt"))

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(load_file, path, name, True)
                for path, name in files
            ]
            results = [f.result(timeout=30) for f in futures]

        assert len(results) == 5
        for sources, pii_report in results:
            assert len(sources) == 1

    def test_pii_scanning_in_thread(self, tmp_path):
        """Verify PII scanning works correctly when run in a thread."""
        import concurrent.futures

        content = "Email: test@example.com, Phone: 555-999-8888"
        file_path = tmp_path / "pii_thread.txt"
        file_path.write_text(content)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(load_file, str(file_path), "pii_thread.txt", True)
            sources, pii_report = future.result(timeout=30)

        assert pii_report["has_pii"] is True
        assert "test@example.com" not in sources[0].content


class TestFileUploadEdgeCases:
    """Test edge cases in file upload handling."""

    def test_file_with_only_whitespace(self, tmp_path):
        file_path = tmp_path / "whitespace.txt"
        file_path.write_text("   \n\n\t  \n  ")

        sources, pii_report = load_file(str(file_path), "whitespace.txt", redact=True)
        assert sources == []

    def test_binary_content_in_text_file(self, tmp_path):
        """Text loader should handle binary-ish content gracefully."""
        file_path = tmp_path / "mixed.txt"
        file_path.write_bytes(b"Normal text \x00\x01\x02 more text")

        sources, pii_report = load_file(str(file_path), "mixed.txt", redact=True)
        # Should not crash, may have partial content
        assert isinstance(sources, list)

    def test_very_long_filename(self, tmp_path):
        long_name = "a" * 200 + ".txt"
        file_path = tmp_path / "short.txt"
        file_path.write_text("Content")

        sources, pii_report = load_file(str(file_path), long_name, redact=True)
        assert len(sources) == 1
        assert sources[0].title == long_name

    def test_file_with_no_extension(self, tmp_path):
        file_path = tmp_path / "noext"
        file_path.write_text("Some content")

        sources, pii_report = load_file(str(file_path), "noext", redact=True)
        assert sources == []  # No extension = unsupported
