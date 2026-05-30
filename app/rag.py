import os
import logging
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models import Source

logger = logging.getLogger("research-agent.rag")


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )


def build_vector_store(sources: list[Source]) -> FAISS:
    """Chunk sources and build a FAISS vector store."""
    logger.info(f"Building vector store from {len(sources)} sources")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    texts = []
    metadatas = []
    for source in sources:
        if not source.content.strip():
            continue
        chunks = splitter.split_text(source.content)
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append({"title": source.title, "url": source.url, "query": source.query})

    if not texts:
        logger.warning("No text chunks to embed")
        return None

    logger.info(f"Embedding {len(texts)} chunks into FAISS")
    vector_store = FAISS.from_texts(texts, get_embeddings(), metadatas=metadatas)
    logger.info("Vector store built successfully")
    return vector_store


def merge_vector_stores(store1: FAISS, store2: FAISS) -> FAISS:
    """Merge two FAISS vector stores into one."""
    if store1 is None:
        return store2
    if store2 is None:
        return store1
    store1.merge_from(store2)
    logger.info("Merged two vector stores")
    return store1


def retrieve_relevant_chunks(vector_store: FAISS, query: str, k: int = 8) -> list[dict]:
    """Retrieve top-k relevant chunks with metadata."""
    if vector_store is None:
        return []

    logger.debug(f"Retrieving top-{k} chunks for: {query[:50]}")
    results = vector_store.similarity_search_with_score(query, k=k)

    chunks = []
    for doc, score in results:
        chunks.append({
            "content": doc.page_content,
            "title": doc.metadata.get("title", ""),
            "url": doc.metadata.get("url", ""),
            "score": float(score),
        })

    if chunks:
        logger.debug(f"Retrieved {len(chunks)} chunks (best score: {chunks[0]['score']:.3f})")
    else:
        logger.debug("No chunks retrieved")
    return chunks
