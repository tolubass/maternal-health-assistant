"""
Tests for the FastAPI endpoints.
Run: pytest tests/test_api.py -v
"""
import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient
from sentence_transformers import SentenceTransformer
import chromadb
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

from app.main import app, state

BASE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def initialise_app_state():
    """
    Manually initialise the app state components once for the whole session.
    This bypasses lifespan triggering issues in pytest and directly sets up
    the same objects the production server uses.
    """
    state.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    chroma_client = chromadb.PersistentClient(
        path=str(BASE_DIR / "data" / "chroma_db")
    )
    state.collection = chroma_client.get_collection("maternal_health_minilm_v1")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY not set — skipping API tests")
    state.groq_client = Groq(api_key=api_key)

    yield

    # Teardown — reset state after session
    state.embedder = None
    state.collection = None
    state.groq_client = None


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


# -------------------------------------------------------
# Tests
# -------------------------------------------------------
def test_health_returns_200(client):
    """Health endpoint must return 200 with status ok and non-zero collection."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["collection_size"] > 0


def test_chat_valid_question(client):
    """A valid question must return an answer and a citations list."""
    response = client.post("/chat", json={
        "question": "What is antenatal care?",
        "history": []
    })
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0
    assert "citations" in data
    assert isinstance(data["citations"], list)


def test_chat_with_history(client):
    """Follow-up question with history must return a valid response."""
    history = [
        {"role": "user", "content": "What is antenatal care?"},
        {"role": "assistant", "content": "Antenatal care is care given during pregnancy."},
    ]
    response = client.post("/chat", json={
        "question": "Tell me more about that.",
        "history": history
    })
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_chat_empty_question_rejected(client):
    """Empty question must be rejected with 422."""
    response = client.post("/chat", json={"question": "", "history": []})
    assert response.status_code == 422


def test_chat_question_too_long_rejected(client):
    """Question over 2000 chars must be rejected with 422."""
    response = client.post("/chat", json={"question": "x" * 2001, "history": []})
    assert response.status_code == 422


def test_chat_invalid_history_role_rejected(client):
    """History with an invalid role must be rejected with 422."""
    response = client.post("/chat", json={
        "question": "What is safe delivery?",
        "history": [{"role": "admin", "content": "some text"}]
    })
    assert response.status_code == 422