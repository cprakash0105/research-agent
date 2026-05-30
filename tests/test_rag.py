import pytest
from unittest.mock import patch, MagicMock
from app.rag import build_vector_store, retrieve_relevant_chunks, merge_vector_stores
from app.models import Source


class TestVectorStoreBuilding:
    """Test FAISS vector store construction."""

    @patch("app.rag.get_embeddings")
    def test_build_from_sources(self, mock_embeddings, sample_sources):
        # Mock embeddings to return fixed-size vectors
        mock_embed = MagicMock()
        mock_embed.embed_documents.return_value = [[0.1] * 768 for _ in range(10)]
        mock_embeddings.return_value = mock_embed

        # Patch FAISS.from_texts
        with patch("app.rag.FAISS.from_texts") as mock_faiss:
            mock_faiss.return_value = MagicMock()
            store = build_vector_store(sample_sources)
            assert mock_faiss.called

    def test_build_from_empty_sources(self):
        store = build_vector_store([])
        assert store is None

    def test_build_from_sources_with_empty_content(self):
        sources = [
            Source(title="Empty", url="https://example.com", content="", query="test"),
            Source(title="Whitespace", url="https://example.com", content="   ", query="test"),
        ]
        store = build_vector_store(sources)
        assert store is None


class TestRetrieval:
    """Test chunk retrieval."""

    def test_retrieve_from_none_store(self):
        chunks = retrieve_relevant_chunks(None, "test query", k=5)
        assert chunks == []

    def test_retrieve_returns_list(self):
        mock_store = MagicMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "test content"
        mock_doc.metadata = {"title": "Test", "url": "https://example.com"}
        mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.5)]

        chunks = retrieve_relevant_chunks(mock_store, "test query", k=5)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "test content"
        assert chunks[0]["title"] == "Test"
        assert chunks[0]["score"] == 0.5


class TestMergeStores:
    """Test vector store merging."""

    def test_merge_both_none(self):
        result = merge_vector_stores(None, None)
        assert result is None

    def test_merge_first_none(self):
        mock_store = MagicMock()
        result = merge_vector_stores(None, mock_store)
        assert result == mock_store

    def test_merge_second_none(self):
        mock_store = MagicMock()
        result = merge_vector_stores(mock_store, None)
        assert result == mock_store

    def test_merge_both_valid(self):
        store1 = MagicMock()
        store2 = MagicMock()
        result = merge_vector_stores(store1, store2)
        store1.merge_from.assert_called_once_with(store2)
        assert result == store1
