"""
Maternal Health Assistant — CLI query interface.
Retrieves grounded answers from the Chroma knowledge base.
Maintains conversation history across turns for natural follow-ups.
"""
from pathlib import Path
import os
import logging
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq, APIStatusError, APIConnectionError
from dotenv import load_dotenv

# -----------------------------
# Setup
# -----------------------------
load_dotenv()
logging.basicConfig(level=logging.WARNING, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"
COLLECTION_NAME = "maternal_health_minilm_v1"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.3-70b-versatile"

# Retrieval settings
TOP_K = 5                      # more context -> better answers
MAX_DISTANCE = 1.4              # cosine distance ceiling; above this = no relevant chunks
MIN_RELEVANT_CHUNKS = 2         # need at least this many under MAX_DISTANCE to attempt an answer

# Conversation memory
MAX_HISTORY_TURNS = 4           # 6 = 3 back-and-forths; keeps prompt size bounded

SYSTEM_PROMPT = """You are a maternal and child health information assistant for Nigeria.
You help pregnant women, new mothers, caregivers, and health workers understand maternal and child health topics using authoritative WHO, Nigerian Federal Ministry of Health, NPHCDA, UNICEF, and NCDC guidelines.

HOW TO ANSWER:
1. Ground every answer in the CONTEXT passages provided below. You may combine, summarize, and synthesize information across passages to give a helpful, complete answer.
2. If the CONTEXT contains related information but does not directly address the exact question, give the user what IS in the context and note what is missing. Do not refuse to answer just because the wording does not match exactly.
3. Only say "I don't have information about that in my knowledge base. Please consult a qualified health worker." when the CONTEXT is genuinely unrelated to the question.
4. Use the CONVERSATION HISTORY (if any) to understand follow-up questions. When the user says "what about that", "and in the third trimester", "tell me more", they are referring to the previous topic. Resolve the reference, then answer using the current CONTEXT.

SAFETY RULES (never break):
- Never diagnose. Never prescribe medication or recommend dosages.
- For emergency symptoms (heavy bleeding, convulsions, loss of consciousness, severe abdominal pain, no fetal movement, newborn fever above 38°C, severe breathing difficulty), tell the user clearly to seek immediate medical care at the nearest health facility.
- Cite each major claim using [n] markers that refer to the numbered CONTEXT passages.
- Use plain language. Keep answers focused and not too long.
"""

NO_INFO_MESSAGE = (
    "I don't have information about that in my knowledge base. "
    "Please consult a qualified health worker for accurate guidance."
)


# -----------------------------
# Components
# -----------------------------
def load_embedder():
    return SentenceTransformer(EMBEDDING_MODEL)


def load_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


def load_groq_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not found in .env file")
    return Groq(api_key=key)


# -----------------------------
# Retrieval
# -----------------------------
def retrieve(query: str, embedder, collection, top_k: int = TOP_K):
    """Embed the query, run similarity search, return chunks with metadata + distance."""
    query_embedding = embedder.encode(query, convert_to_numpy=True).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )
    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return chunks


def filter_relevant(chunks, max_distance: float = MAX_DISTANCE):
    """Keep only chunks below the distance ceiling (i.e. sufficiently similar)."""
    return [c for c in chunks if c["distance"] <= max_distance]


MAX_CHARS_PER_CHUNK = 800  # cap chunk text sent to LLM to stay under TPM limits


def build_context(chunks):
    """Format retrieved chunks into a numbered context block for the LLM."""
    parts = []
    for i, c in enumerate(chunks, start=1):
        src = c["metadata"].get("source", "unknown")
        fname = c["metadata"].get("filename", "unknown")
        text = c["text"]
        if len(text) > MAX_CHARS_PER_CHUNK:
            text = text[:MAX_CHARS_PER_CHUNK] + " ..."
        parts.append(f"[{i}] Source: {src} | {fname}\n{text}")
    return "\n\n---\n\n".join(parts)


def format_citations(chunks):
    """Citation list shown after the answer."""
    lines = []
    for i, c in enumerate(chunks, start=1):
        src = c["metadata"].get("source", "unknown")
        fname = c["metadata"].get("filename", "unknown")
        lines.append(f"  [{i}] {src} — {fname}")
    return "\n".join(lines)


# -----------------------------
# Generation with conversation history
# -----------------------------
def generate_answer(query: str, context: str, history: list, client):
    """
    Call Groq with: system prompt + prior conversation history + current context + current question.
    Catches rate-limit and connection errors and returns a user-friendly message instead of crashing.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({
        "role": "user",
        "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}",
    })

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.2,
            max_tokens=700,
            messages=messages,
        )
        return response.choices[0].message.content
    except APIStatusError as e:
        if e.status_code == 413 or "rate_limit" in str(e).lower():
            return (
                "I'm receiving too many requests right now. "
                "Please wait about 30 seconds and ask again. "
                "(Groq free-tier per-minute token limit reached.)"
            )
        return f"I hit an error while generating the answer. Please try again. (Details: {e.status_code})"
    except APIConnectionError:
        return "I couldn't reach the language model. Check your internet connection and try again."
    except Exception as e:
        return f"Unexpected error while generating the answer. Please try again. (Details: {type(e).__name__})"

def trim_history(history: list, max_turns: int = MAX_HISTORY_TURNS) -> list:
    """Keep only the last `max_turns` messages so the prompt doesn't grow forever."""
    if len(history) <= max_turns:
        return history
    return history[-max_turns:]


# -----------------------------
# Main CLI loop
# -----------------------------
def main():
    print("Loading components... (first run takes ~10 seconds)")
    embedder = load_embedder()
    collection = load_collection()
    client = load_groq_client()
    print(f"Ready. Collection size: {collection.count()} chunks.")
    print("Type your question. Commands: 'clear' to reset memory, 'quit' to exit.\n")

    # Conversation history: list of {"role": "user"|"assistant", "content": str}
    history = []

    while True:
        try:
            query = input("Q: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not query:
            continue
        if query.lower() in {"quit", "exit", "q"}:
            print("Goodbye.")
            break
        if query.lower() == "clear":
            history = []
            print("Conversation history cleared.\n")
            continue

        # Retrieve fresh context for THIS question (do not rely on memory of old chunks)
        all_chunks = retrieve(query, embedder, collection)
        relevant = filter_relevant(all_chunks)

        if len(relevant) < MIN_RELEVANT_CHUNKS:
            answer = NO_INFO_MESSAGE
            sources_text = "  (no sufficiently relevant sources found)"
        else:
            context = build_context(relevant)
            answer = generate_answer(query, context, history, client)
            sources_text = format_citations(relevant)

        # Update history with this turn
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})
        history = trim_history(history)

        print("\n" + "=" * 70)
        print("ANSWER:")
        print(answer)
        print("\nSOURCES USED:")
        print(sources_text)
        print("=" * 70 + "\n")


if __name__ == "__main__":
    main()