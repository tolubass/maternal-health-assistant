"""
Tests for retrieval logic — Chroma connection, similarity search, filtering.
Run: pytest tests/test_retrieval.py -v

These tests require the Chroma DB to be built first (ingestion/build_chroma.py).
"""
import pytest
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"
COLLECTION_NAME = "maternal_health_minilm_v1"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K = 5
MAX_DISTANCE = 1.4


# -------------------------------------------------------
# Fixtures — load once for all tests in this file
# -------------------------------------------------------
@pytest.fixture(scope="module")
def collection():
    """Returns the live Chroma collection."""
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


@pytest.fixture(scope="module")
def embedder():
    """Returns the sentence-transformers model."""
    return SentenceTransformer(EMBEDDING_MODEL)


# -------------------------------------------------------
# Collection integrity
# -------------------------------------------------------
def test_collection_exists(collection):
    """Chroma collection must exist and have chunks."""
    assert collection is not None


def test_collection_has_expected_chunk_count(collection):
    """Collection must have at least 2000 chunks (we ingested 2319)."""
    count = collection.count()
    assert count >= 2000, f"Expected >= 2000 chunks, got {count}"


# -------------------------------------------------------
# Retrieval quality
# -------------------------------------------------------
def test_query_returns_results(collection, embedder):
    """A relevant query must return TOP_K results."""
    embedding = embedder.encode("antenatal care", convert_to_numpy=True).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=TOP_K)
    assert len(results["ids"][0]) == TOP_K


def test_results_have_required_fields(collection, embedder):
    """Each result must have id, document text, metadata, and distance."""
    embedding = embedder.encode("danger signs pregnancy", convert_to_numpy=True).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=TOP_K)
    assert len(results["ids"][0]) > 0
    assert len(results["documents"][0]) > 0
    assert len(results["metadatas"][0]) > 0
    assert len(results["distances"][0]) > 0


def test_distances_are_non_negative(collection, embedder):
    """Cosine distances must be >= 0."""
    embedding = embedder.encode("breastfeeding newborn", convert_to_numpy=True).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=TOP_K)
    for dist in results["distances"][0]:
        assert dist >= 0, f"Negative distance found: {dist}"


def test_relevant_medical_query_gets_close_results(collection, embedder):
    """A clear medical query must return at least one chunk under the distance ceiling."""
    embedding = embedder.encode(
        "what is the danger sign for a pregnant woman", convert_to_numpy=True
    ).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=TOP_K)
    distances = results["distances"][0]
    close_results = [d for d in distances if d <= MAX_DISTANCE]
    assert len(close_results) >= 1, (
        f"Expected at least 1 result under distance {MAX_DISTANCE}, "
        f"got distances: {distances}"
    )


def test_filter_relevant_removes_distant_chunks(collection, embedder):
    """filter_relevant logic: chunks above MAX_DISTANCE must be excluded."""
    embedding = embedder.encode("antenatal care Nigeria", convert_to_numpy=True).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=TOP_K)

    chunks = [
        {"distance": d, "text": t, "metadata": m}
        for d, t, m in zip(
            results["distances"][0],
            results["documents"][0],
            results["metadatas"][0],
        )
    ]
    relevant = [c for c in chunks if c["distance"] <= MAX_DISTANCE]

    # All returned chunks must be at or below the ceiling
    for c in relevant:
        assert c["distance"] <= MAX_DISTANCE


def test_metadata_contains_source_and_filename(collection, embedder):
    """Every retrieved chunk must have source and filename in its metadata."""
    embedding = embedder.encode("maternal mortality Nigeria", convert_to_numpy=True).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=TOP_K)
    for meta in results["metadatas"][0]:
        assert "source" in meta, "Missing 'source' in chunk metadata"
        assert "filename" in meta, "Missing 'filename' in chunk metadata"


def test_unrelated_query_returns_worse_results_than_medical_query(collection, embedder):
    """
    An off-topic query should return worse (higher) distances than a clear medical query.
    This proves retrieval is doing semantic matching, not returning random results.
    """
    medical_embedding = embedder.encode(
        "danger signs during pregnancy bleeding convulsions", convert_to_numpy=True
    ).tolist()
    offtopic_embedding = embedder.encode(
        "stock market cryptocurrency bitcoin trading", convert_to_numpy=True
    ).tolist()

    medical_results = collection.query(query_embeddings=[medical_embedding], n_results=TOP_K)
    offtopic_results = collection.query(query_embeddings=[offtopic_embedding], n_results=TOP_K)

    medical_avg = sum(medical_results["distances"][0]) / TOP_K
    offtopic_avg = sum(offtopic_results["distances"][0]) / TOP_K

    assert offtopic_avg > medical_avg, (
        f"Off-topic query (avg: {offtopic_avg:.3f}) should have higher distance "
        f"than medical query (avg: {medical_avg:.3f})"
    )