"""
Validate processed chunks before embedding.

Checks:
- Every chunk has required fields (chunk_id, text, metadata)
- No chunk is below the minimum token threshold
- Metadata contains source and filename
- No duplicate chunk IDs

Run: python ingestion/validate_chunks.py
"""
from pathlib import Path
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
CHUNKS_FILE = BASE_DIR / "data" / "processed" / "chunks.jsonl"

REQUIRED_FIELDS = {"chunk_id", "text", "metadata"}
REQUIRED_METADATA = {"source", "filename"}
MIN_TOKENS = 20  # ~80 characters — discard tiny fragments


def validate(chunks_file: Path = CHUNKS_FILE) -> bool:
    if not chunks_file.exists():
        logger.error(f"Chunks file not found: {chunks_file}")
        return False

    chunks = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.error(f"Line {i}: invalid JSON — {e}")
                return False

    logger.info(f"Loaded {len(chunks)} chunks from {chunks_file.name}")

    errors = []
    seen_ids: set[str] = set()

    for i, chunk in enumerate(chunks):
        # Required top-level fields
        missing = REQUIRED_FIELDS - chunk.keys()
        if missing:
            errors.append(f"Chunk {i}: missing fields {missing}")
            continue

        chunk_id = chunk["chunk_id"]
        text = chunk["text"]
        metadata = chunk["metadata"]

        # Duplicate IDs
        if chunk_id in seen_ids:
            errors.append(f"Chunk {i}: duplicate chunk_id '{chunk_id}'")
        seen_ids.add(chunk_id)

        # Minimum text length (approximate tokens by dividing chars by 4)
        approx_tokens = len(text) // 4
        if approx_tokens < MIN_TOKENS:
            errors.append(
                f"Chunk {i} (id={chunk_id}): too short "
                f"({approx_tokens} tokens, min={MIN_TOKENS})"
            )

        # Required metadata keys
        if not isinstance(metadata, dict):
            errors.append(f"Chunk {i}: metadata is not a dict")
            continue
        missing_meta = REQUIRED_METADATA - metadata.keys()
        if missing_meta:
            errors.append(f"Chunk {i} (id={chunk_id}): missing metadata keys {missing_meta}")

    if errors:
        logger.error(f"Validation FAILED — {len(errors)} error(s):")
        for err in errors[:20]:  # cap output to first 20
            logger.error(f"  {err}")
        if len(errors) > 20:
            logger.error(f"  ... and {len(errors) - 20} more")
        return False

    logger.info(f"Validation PASSED — {len(chunks)} chunks, {len(seen_ids)} unique IDs")
    return True


if __name__ == "__main__":
    ok = validate()
    sys.exit(0 if ok else 1)
