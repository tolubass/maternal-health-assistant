"""
Enrich chunk metadata after chunking and before embedding.

Adds derived fields that improve retrieval and citation quality:
- topic_area: broad clinical topic inferred from filename keywords
- language: "en" (all current sources are English)
- char_count: length of the chunk text

Run: python ingestion/enrich_metadata.py
"""
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
CHUNKS_FILE = BASE_DIR / "data" / "processed" / "chunks.jsonl"

# Maps lowercase filename substrings → topic label
_TOPIC_KEYWORDS: list[tuple[str, str]] = [
    ("antenatal", "antenatal_care"),
    ("postnatal", "postnatal_care"),
    ("labour", "labour_delivery"),
    ("delivery", "labour_delivery"),
    ("childbirth", "labour_delivery"),
    ("newborn", "newborn_care"),
    ("infant", "infant_care"),
    ("breastfeed", "infant_feeding"),
    ("feeding", "infant_feeding"),
    ("nutrition", "nutrition"),
    ("immuniz", "immunization"),
    ("vaccin", "immunization"),
    ("malaria", "malaria"),
    ("hiv", "hiv_aids"),
    ("infection", "infection_control"),
    ("emergency", "emergency_obstetric"),
    ("haemorrhage", "emergency_obstetric"),
    ("hemorrhage", "emergency_obstetric"),
    ("eclampsia", "emergency_obstetric"),
    ("growth", "child_growth"),
    ("mortality", "maternal_mortality"),
    ("safe_mother", "safe_motherhood"),
]


def infer_topic(filename: str) -> str:
    fname_lower = filename.lower()
    for keyword, topic in _TOPIC_KEYWORDS:
        if keyword in fname_lower:
            return topic
    return "general"


def enrich(chunks_file: Path = CHUNKS_FILE) -> int:
    if not chunks_file.exists():
        logger.error(f"Chunks file not found: {chunks_file}")
        return 0

    enriched = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunk = json.loads(line)
            meta = chunk.get("metadata", {})

            meta.setdefault("language", "en")
            meta["char_count"] = len(chunk.get("text", ""))
            meta["topic_area"] = infer_topic(meta.get("filename", ""))

            chunk["metadata"] = meta
            enriched.append(chunk)

    with open(chunks_file, "w", encoding="utf-8") as f:
        for chunk in enriched:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    logger.info(f"Enriched {len(enriched)} chunks in {chunks_file.name}")
    return len(enriched)


if __name__ == "__main__":
    count = enrich()
    logger.info(f"Done — {count} chunks enriched")
