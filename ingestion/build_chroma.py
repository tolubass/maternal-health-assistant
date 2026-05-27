from pathlib import Path
import json
import logging
import chromadb

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
EMBEDDED_FILE = BASE_DIR / "data" / "embeddings" / "chunks_embedded.jsonl"
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"
COLLECTION_NAME = "maternal_health_minilm_v1"


def load_embedded_chunks(path: Path):
    """Read chunks_embedded.jsonl line by line."""
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    logger.info(f"Loaded {len(chunks)} embedded chunks from {path.name}")
    return chunks


def sanitize_metadata(meta: dict) -> dict:
    """Chroma only accepts str, int, float, bool, or None as metadata values."""
    clean = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean


def main():
    if not EMBEDDED_FILE.exists():
        logger.error(f"Embedded chunks file not found: {EMBEDDED_FILE}")
        logger.error("Run ingestion/embed_store.py first.")
        return

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Fresh start: drop the collection if it exists, then recreate.
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing:
        logger.info(f"Deleting existing collection '{COLLECTION_NAME}'")
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(f"Created collection '{COLLECTION_NAME}'")

    chunks = load_embedded_chunks(EMBEDDED_FILE)

    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    embeddings = [c["embedding"] for c in chunks]
    metadatas = [sanitize_metadata(c["metadata"]) for c in chunks]

    # Upsert in batches to avoid memory spikes.
    BATCH = 500
    for i in range(0, len(chunks), BATCH):
        collection.add(
            ids=ids[i:i + BATCH],
            documents=documents[i:i + BATCH],
            embeddings=embeddings[i:i + BATCH],
            metadatas=metadatas[i:i + BATCH],
        )
        logger.info(f"Inserted {min(i + BATCH, len(chunks))} / {len(chunks)}")

    count = collection.count()
    logger.info(f"Done. Collection now holds {count} chunks at {CHROMA_DIR}")


if __name__ == "__main__":
    main()