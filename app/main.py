"""
Maternal Health Assistant — FastAPI server.
LLM strategy: Google Gemini Flash (primary) → Groq Llama 3.3 (fallback).
All requests pass through the four-layer safety stack.
"""
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional
import os
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import chromadb
from sentence_transformers import SentenceTransformer
from google import genai as google_genai
from google.genai import types as genai_types
from groq import Groq, APIStatusError, APIConnectionError
from dotenv import load_dotenv

from safety import (
    is_emergency,
    check_input,
    BLOCK_MESSAGES,
    validate_output,
    UNSAFE_OUTPUT_FALLBACK,
    EMERGENCY_RESPONSE,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------
# Paths & constants
# -------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"
COLLECTION_NAME = "maternal_health_minilm_v1"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL   = "llama-3.3-70b-versatile"

TOP_K = 8
MAX_DISTANCE = 1.4
MIN_RELEVANT_CHUNKS = 2
MAX_CHARS_PER_CHUNK = 800
MAX_HISTORY_TURNS = 6

SYSTEM_PROMPT = """You are a maternal and child health information assistant for Nigeria.
You help pregnant women, new mothers, caregivers, and health workers understand maternal
and child health topics using authoritative WHO, Nigerian Federal Ministry of Health,
NPHCDA, UNICEF, and NCDC guidelines.

HOW TO ANSWER:
1. Ground every answer in the CONTEXT passages provided. Combine, summarize, and
   synthesize across passages to give a helpful, complete answer.
2. If the CONTEXT contains related but not perfectly matching information, still give
   the most complete answer you can — draw on everything in the context that is relevant.
3. Only say you have no information when the CONTEXT is genuinely unrelated to the question.
4. Use the CONVERSATION HISTORY to handle follow-up requests. When asked to "continue",
   "tell me more", or "elaborate", build directly on your previous answer and go deeper —
   never start over, never say you cannot continue.
5. Never stop mid-sentence. Every response must be a complete, finished answer.

SAFETY RULES (never break):
- Never diagnose. Never prescribe medication or recommend dosages.
- For ANY emergency symptom — heavy bleeding, convulsions, loss of consciousness,
  severe abdominal pain, no fetal movement, newborn fever above 38°C, severe breathing
  difficulty — tell the user immediately to seek care at the nearest health facility.
- Cite each major claim using [n] markers that refer to the numbered CONTEXT passages.
- Use plain, clear language. Structure answers with headings and bullet points where helpful.
"""

GREETING_TRIGGERS = {
    "hi", "hello", "hey", "hiya", "heya", "yo", "sup", "wassup",
    "whatsup", "what's up", "whaddup",
    "good morning", "good afternoon", "good evening", "good day",
    "good night", "gd morning", "gd afternoon", "gd evening",
    "gud morning", "gud afternoon", "gud evening",
    "morning", "afternoon", "evening",
    "how are you", "how are you doing", "how are you today",
    "how r you", "how r u", "how are u", "how ru",
    "how are you going", "how you doing", "how u doing",
    "how you dey", "how far", "how far now", "how na",
    "how body", "how life", "how now", "how things",
    "how e dey", "wetin dey", "e don do", "guy how far",
    "bro how far", "sis how far",
    "hello how are you", "hello how are you doing",
    "hello how r u", "hello how are u",
    "hi how are you", "hi how are you doing",
    "hi how r u", "hi how are u",
    "hey how are you", "hey how r u",
    "hey how far", "hi how far",
    "greetings", "salutations", "howdy", "aloha",
    "hi there", "hello there", "hey there", "hiya there",
    "e kaaro", "e kaasan", "e kaale", "bawo ni",
    "nne kedu", "kedu", "how body na", "how you see life",
    "e nle", "ndewo", "nnoo",
    "good to meet you", "nice to meet you", "pleased to meet you",
    "just saying hi", "just checking in",
    "ok", "okay", "ok thanks", "okay thanks", "thank you",
    "thanks", "thank u", "cheers", "noted", "alright",
    "cool", "great", "awesome", "nice", "wow",
    "i see", "understood", "got it",
}

GREETING_RESPONSE = (
    "Hello! Welcome to the Maternal Health Assistant.\n\n"
    "I'm here to help you with questions about pregnancy, antenatal care, "
    "childbirth, postpartum care, newborn health, nutrition, and more — "
    "all grounded in WHO and Nigerian health guidelines.\n\n"
    "How can I help you today?"
)


# -------------------------------------------------------
# App state
# -------------------------------------------------------
class AppState:
    embedder: Optional[SentenceTransformer] = None
    collection = None
    gemini_client = None   # google.genai.Client
    groq_client: Optional[Groq] = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading embedding model...")
    state.embedder = SentenceTransformer(EMBEDDING_MODEL)

    logger.info("Connecting to Chroma...")
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    state.collection = chroma_client.get_collection(COLLECTION_NAME)
    logger.info(f"Chroma ready — {state.collection.count()} chunks")

    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key:
        state.gemini_client = google_genai.Client(api_key=google_key)
        logger.info(f"Gemini client ready ({GEMINI_MODEL})")
    else:
        logger.warning("GOOGLE_API_KEY not set — Gemini unavailable, Groq only")

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        state.groq_client = Groq(api_key=groq_key)
        logger.info(f"Groq client ready ({GROQ_MODEL}) — fallback")
    else:
        logger.warning("GROQ_API_KEY not set — no fallback LLM available")

    if not google_key and not groq_key:
        raise RuntimeError("No LLM API keys set. Add GOOGLE_API_KEY or GROQ_API_KEY to .env")

    yield
    logger.info("Shutting down")


# -------------------------------------------------------
# FastAPI app
# -------------------------------------------------------
_cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app = FastAPI(
    title="Maternal Health Assistant API",
    description="RAG-powered maternal and child health information for Nigeria.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# -------------------------------------------------------
# Schemas
# -------------------------------------------------------
class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: list[Message] = Field(default_factory=list)


class CitationItem(BaseModel):
    index: int
    source: str
    filename: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationItem]


# -------------------------------------------------------
# Continuation-aware query expansion
# -------------------------------------------------------
_CONTINUATION_TRIGGERS = frozenset({
    # explicit continuations
    "continue", "go on", "keep going", "go ahead", "proceed",
    "please continue", "continue please", "go on please",
    # requests for more
    "more", "tell me more", "more details", "more information",
    "more info", "elaborate", "expand", "expand on that",
    "can you elaborate", "please elaborate", "give me more",
    "what else", "what more", "anything else",
    # short affirmatives that signal continuation
    "yes please", "ok continue", "okay continue",
    "and then", "and?", "so?",
})


def _expand_query(question: str, history: list[dict]) -> str:
    """
    For short follow-up phrases like 'continue' or 'tell me more',
    substitute the last substantive user question so vector retrieval
    finds relevant chunks instead of noise.
    The original question is still passed to the LLM unchanged.
    """
    normalized = question.strip().lower().rstrip("!.,? ")
    if normalized in _CONTINUATION_TRIGGERS:
        for msg in reversed(history):
            if msg["role"] == "user" and len(msg["content"].strip()) > 30:
                logger.info(
                    f"Continuation detected ('{normalized}') — "
                    f"expanding query from history: '{msg['content'][:60]}'"
                )
                return msg["content"]
    return question


# -------------------------------------------------------
# Retrieval helpers
# -------------------------------------------------------
def retrieve(question: str) -> list[dict]:
    embedding = state.embedder.encode(
        question, convert_to_numpy=True
    ).tolist()
    results = state.collection.query(
        query_embeddings=[embedding],
        n_results=TOP_K,
    )
    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id":       results["ids"][0][i],
            "text":     results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return chunks


def filter_relevant(chunks: list[dict]) -> list[dict]:
    return [c for c in chunks if c["distance"] <= MAX_DISTANCE]


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        src   = c["metadata"].get("source", "unknown")
        fname = c["metadata"].get("filename", "unknown")
        text  = c["text"][:MAX_CHARS_PER_CHUNK]
        parts.append(f"[{i}] Source: {src} | {fname}\n{text}")
    return "\n\n---\n\n".join(parts)


def build_citations(chunks: list[dict]) -> list[CitationItem]:
    return [
        CitationItem(
            index=i,
            source=c["metadata"].get("source", "unknown"),
            filename=c["metadata"].get("filename", "unknown"),
        )
        for i, c in enumerate(chunks, start=1)
    ]


def trim_history(history: list[Message]) -> list[dict]:
    recent = (
        history[-MAX_HISTORY_TURNS:]
        if len(history) > MAX_HISTORY_TURNS
        else history
    )
    compressed = []
    for msg in recent:
        content = msg.content
        # Keep enough of previous answers for meaningful continuation context
        if msg.role == "assistant" and len(content) > 1200:
            content = content[:1200] + " ..."
        compressed.append({"role": msg.role, "content": content})
    return compressed


# -------------------------------------------------------
# LLM calls
# -------------------------------------------------------
def call_gemini(question: str, context: str, history: list[dict]) -> str:
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            genai_types.Content(
                role=role,
                parts=[genai_types.Part(text=msg["content"])],
            )
        )
    contents.append(
        genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=f"CONTEXT:\n{context}\n\nQUESTION: {question}")],
        )
    )
    response = state.gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=4096,
        ),
    )
    # Collect text from all parts so nothing is silently dropped
    text = ""
    try:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                text += part.text
    except Exception:
        text = response.text or ""

    if not text:
        raise ValueError("Gemini returned an empty response")
    return text


def call_groq(question: str, context: str, history: list[dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({
        "role": "user",
        "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}",
    })
    try:
        response = state.groq_client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.2,
            max_tokens=2048,
            messages=messages,
        )
        return response.choices[0].message.content
    except APIStatusError as e:
        # 429 = rate limit; surface it so callers can inform the user
        if e.status_code == 429 or "rate_limit" in str(e).lower():
            raise HTTPException(
                status_code=429,
                detail="Both LLMs are rate-limited. Please wait 30 seconds.",
            )
        raise HTTPException(status_code=502, detail=f"LLM error: {e.status_code}")
    except APIConnectionError:
        raise HTTPException(status_code=503, detail="Cannot reach language model.")


def call_llm(question: str, context: str, history: list[dict]) -> str:
    """Primary: Gemini Flash. Fallback: Groq Llama 3.3 70B."""
    if state.gemini_client is not None:
        try:
            answer = call_gemini(question, context, history)
            logger.info("Response from Gemini Flash")
            return answer
        except Exception as e:
            logger.warning(f"Gemini failed ({type(e).__name__}), falling back to Groq")

    if state.groq_client is not None:
        logger.info("Response from Groq (fallback)")
        return call_groq(question, context, history)

    raise HTTPException(
        status_code=503,
        detail="No language model available. Check API keys in .env file.",
    )


# -------------------------------------------------------
# API Endpoints
# -------------------------------------------------------
@app.get("/health", summary="Liveness check")
def health():
    return {
        "status": "ok",
        "collection_size": (
            state.collection.count() if state.collection else 0
        ),
        "gemini_available": state.gemini_client is not None,
        "groq_available": state.groq_client is not None,
    }


@app.post("/chat", response_model=ChatResponse, summary="Ask a health question")
def chat(request: ChatRequest):
    """
    Four-layer safety pipeline:
      1. Emergency detection  → immediate hardcoded response
      2. Input filter         → block diagnosis/prescription/off-topic
      3. Retrieval + LLM      → Gemini primary, Groq fallback
      4. Output validation    → reject prohibited content
    """
    question = request.question

    # Layer 1: Emergency
    if is_emergency(question):
        logger.warning(f"Emergency: '{question[:80]}'")
        return ChatResponse(answer=EMERGENCY_RESPONSE, citations=[])

    # Greeting shortcut
    normalized = question.strip().lower().rstrip("!.,?")
    if normalized in GREETING_TRIGGERS:
        return ChatResponse(answer=GREETING_RESPONSE, citations=[])

    # Layer 2: Input filter
    blocked, reason = check_input(question)
    if blocked:
        return ChatResponse(answer=BLOCK_MESSAGES[reason], citations=[])

    # Layer 3: Retrieve and generate
    history = trim_history(request.history)

    # For continuation phrases ("continue", "tell me more", etc.) use the
    # last substantive user question for retrieval so we get relevant chunks.
    retrieval_query = _expand_query(question, history)

    chunks = retrieve(retrieval_query)
    relevant = filter_relevant(chunks)
    chunks_found = len(relevant) >= MIN_RELEVANT_CHUNKS

    if not chunks_found:
        return ChatResponse(
            answer=(
                "I don't have information about that in my knowledge base. "
                "Please consult a qualified health worker for accurate guidance."
            ),
            citations=[],
        )

    context = build_context(relevant)
    answer  = call_llm(question, context, history)

    # Layer 4: Output validation
    is_safe, _ = validate_output(answer, chunks_were_found=chunks_found)
    if not is_safe:
        logger.warning(f"Output blocked: '{question[:80]}'")
        return ChatResponse(answer=UNSAFE_OUTPUT_FALLBACK, citations=[])

    citations = build_citations(relevant)
    return ChatResponse(answer=answer, citations=citations)


# -------------------------------------------------------
# Serve React frontend (must be mounted AFTER API routes)
# -------------------------------------------------------
_frontend_dist = BASE_DIR / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(_frontend_dist), html=True),
        name="frontend",
    )
