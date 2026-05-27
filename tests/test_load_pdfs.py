"""
Tests for ingestion/load_pdfs.py
Run: pytest tests/test_load_pdfs.py -v
"""
import pytest
from pathlib import Path
from ingestion.load_pdfs import PDFLoader

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"


# Load PDFs ONCE and share across all tests in this session
@pytest.fixture(scope="session")
def documents():
    loader = PDFLoader(data_dir=RAW_DIR)
    return loader.load_pdfs()


def test_loader_finds_pdfs(documents):
    assert len(documents) > 0


def test_each_document_has_required_keys(documents):
    for doc in documents:
        assert "text" in doc
        assert "metadata" in doc


def test_metadata_has_required_fields(documents):
    required = {"filename", "source", "num_pages", "num_characters"}
    for doc in documents:
        missing = required - set(doc["metadata"].keys())
        assert not missing, f"Missing: {missing} in {doc['metadata'].get('filename')}"


def test_documents_have_non_empty_text(documents):
    non_empty = [d for d in documents if d["text"].strip()]
    ratio = len(non_empty) / len(documents)
    assert ratio >= 0.90, f"Only {ratio:.0%} of documents have text"


def test_raises_on_missing_directory():
    with pytest.raises(FileNotFoundError):
        PDFLoader(data_dir=Path("/does/not/exist"))


def test_num_pages_is_positive(documents):
    for doc in documents:
        assert doc["metadata"]["num_pages"] >= 1