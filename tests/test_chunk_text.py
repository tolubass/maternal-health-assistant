"""
Tests for ingestion/chunk_text.py
Run: pytest tests/test_chunk_text.py -v
"""
import pytest
from ingestion.chunk_text import ChunkingConfig, TextChunker, DocumentProcessor, TextCleaner
from pathlib import Path


# -------------------------------------------------------
# Fixtures
# -------------------------------------------------------
@pytest.fixture
def default_config():
    return ChunkingConfig(chunk_size=600, chunk_overlap=100, min_chunk_size=100)


@pytest.fixture
def chunker(default_config):
    return TextChunker(default_config)


@pytest.fixture
def sample_document():
    return {
        "text": (
            "Antenatal care (ANC) is care provided by skilled health-care professionals "
            "to pregnant women and adolescent girls in order to ensure the best health "
            "conditions for both mother and baby during pregnancy.\n\n"
            "The contacts should include: nutritional interventions, maternal and foetal "
            "assessments, preventive measures, health system interventions and health "
            "promotion.\n\n"
            "Women should receive at least eight contacts during pregnancy to reduce "
            "perinatal mortality and improve their experience of care."
        ),
        "metadata": {
            "filename": "test_anc.pdf",
            "source": "who",
            "num_pages": 1,
            "num_characters": 500,
        },
    }


# -------------------------------------------------------
# Config validation
# -------------------------------------------------------
def test_config_rejects_overlap_larger_than_chunk():
    with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
        ChunkingConfig(chunk_size=100, chunk_overlap=100)


def test_config_rejects_min_larger_than_chunk():
    with pytest.raises(ValueError, match="min_chunk_size must be less than chunk_size"):
        ChunkingConfig(chunk_size=100, chunk_overlap=10, min_chunk_size=200)


# -------------------------------------------------------
# Chunking behaviour
# -------------------------------------------------------
def test_chunker_produces_chunks(chunker, sample_document):
    chunks = chunker.chunk_document(sample_document)
    assert len(chunks) > 0, "Expected at least one chunk from a non-empty document"


def test_chunks_have_required_keys(chunker, sample_document):
    chunks = chunker.chunk_document(sample_document)
    for chunk in chunks:
        assert "chunk_id" in chunk
        assert "text" in chunk
        assert "metadata" in chunk


def test_chunk_text_is_non_empty(chunker, sample_document):
    chunks = chunker.chunk_document(sample_document)
    for chunk in chunks:
        assert chunk["text"].strip(), "Chunk text must not be empty"


def test_chunk_id_contains_filename_stem(chunker, sample_document):
    """Chunk IDs should be derived from the source filename."""
    chunks = chunker.chunk_document(sample_document)
    for chunk in chunks:
        assert "test_anc" in chunk["chunk_id"], (
            f"Chunk ID '{chunk['chunk_id']}' should contain filename stem 'test_anc'"
        )


def test_empty_document_returns_no_chunks(chunker):
    doc = {"text": "", "metadata": {"filename": "empty.pdf", "source": "who"}}
    chunks = chunker.chunk_document(doc)
    assert chunks == [], "Empty document should produce zero chunks"


def test_whitespace_only_document_returns_no_chunks(chunker):
    doc = {"text": "   \n\n\t  ", "metadata": {"filename": "blank.pdf", "source": "who"}}
    chunks = chunker.chunk_document(doc)
    assert chunks == [], "Whitespace-only document should produce zero chunks"


def test_metadata_is_preserved_in_chunks(chunker, sample_document):
    """Original metadata fields must be present in every chunk."""
    chunks = chunker.chunk_document(sample_document)
    for chunk in chunks:
        assert chunk["metadata"]["filename"] == "test_anc.pdf"
        assert chunk["metadata"]["source"] == "who"


def test_token_count_recorded_in_metadata(chunker, sample_document):
    chunks = chunker.chunk_document(sample_document)
    for chunk in chunks:
        assert "token_count" in chunk["metadata"]
        assert chunk["metadata"]["token_count"] > 0


# -------------------------------------------------------
# Text cleaner
# -------------------------------------------------------
def test_cleaner_removes_excessive_whitespace():
    cleaned = TextCleaner.clean_text("hello    world")
    assert "  " not in cleaned


def test_cleaner_handles_empty_string():
    assert TextCleaner.clean_text("") == ""


def test_cleaner_strips_leading_trailing_whitespace():
    assert TextCleaner.clean_text("  hello  ") == "hello"