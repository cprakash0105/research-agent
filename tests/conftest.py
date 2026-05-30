import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test env vars
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-key")
os.environ.setdefault("AUTH_USERNAME", "testuser")
os.environ.setdefault("AUTH_PASSWORD", "testpass")


@pytest.fixture
def sample_sources():
    from app.models import Source
    return [
        Source(title="Source 1", url="https://example.com/1", content="AI is transforming drug discovery by accelerating molecule screening.", query="AI drug discovery"),
        Source(title="Source 2", url="https://example.com/2", content="Machine learning models can predict protein folding structures.", query="AI drug discovery"),
        Source(title="Source 3", url="https://example.com/3", content="Clinical trials are being optimized using reinforcement learning.", query="AI clinical trials"),
    ]


@pytest.fixture
def sample_text_with_pii():
    return """
    John Smith works at Acme Corp. His email is john.smith@acme.com and his phone
    number is 555-123-4567. His SSN is 123-45-6789. He lives at 123 Main St, 
    Springfield, IL 62701.
    """


@pytest.fixture
def sample_text_no_pii():
    return """
    GraphRAG combines knowledge graphs with retrieval-augmented generation.
    It enables multi-hop reasoning across documents and reduces hallucination
    by constraining the answer space through graph structure.
    """


@pytest.fixture
def tmp_text_file(tmp_path):
    content = "This is a test document about quantum computing applications in finance."
    file_path = tmp_path / "test_doc.txt"
    file_path.write_text(content)
    return str(file_path)


@pytest.fixture
def tmp_pdf_file(tmp_path):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Test PDF content about machine learning.", ln=True)
    pdf.cell(0, 10, "Neural networks are used for pattern recognition.", ln=True)
    file_path = tmp_path / "test_doc.pdf"
    pdf.output(str(file_path))
    return str(file_path)
