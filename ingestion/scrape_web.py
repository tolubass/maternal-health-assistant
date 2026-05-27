"""
Web scraper for authoritative maternal health sources.

Fetches content from verified WHO, UNFPA, and related public health pages,
chunks the text, embeds with the same model used for PDFs, and UPSERTS into
the existing Chroma collection so existing PDF chunks are never touched.

Run from project root:
    python ingestion/scrape_web.py

Re-runnable safely: uses upsert so duplicate chunk IDs are overwritten, not
duplicated.
"""
from pathlib import Path
import json
import logging
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# -------------------------------------------------------
# Verified authoritative sources (all confirmed reachable)
# -------------------------------------------------------
WEB_SOURCES = [
    # ---- WHO Fact Sheets ----
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/maternal-mortality",
        "source": "who_web",
        "title": "WHO: Maternal Mortality",
        "topic": "maternal_mortality",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/newborns-reducing-mortality",
        "source": "who_web",
        "title": "WHO: Newborn Mortality",
        "topic": "newborn_care",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/preterm-birth",
        "source": "who_web",
        "title": "WHO: Preterm Birth",
        "topic": "preterm_birth",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/anaemia",
        "source": "who_web",
        "title": "WHO: Anaemia",
        "topic": "nutrition",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/infant-and-young-child-feeding",
        "source": "who_web",
        "title": "WHO: Infant and Young Child Feeding",
        "topic": "infant_feeding",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/malnutrition",
        "source": "who_web",
        "title": "WHO: Malnutrition",
        "topic": "nutrition",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/family-planning-contraception",
        "source": "who_web",
        "title": "WHO: Family Planning and Contraception",
        "topic": "family_planning",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/female-genital-mutilation",
        "source": "who_web",
        "title": "WHO: Female Genital Mutilation",
        "topic": "maternal_health",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/malaria",
        "source": "who_web",
        "title": "WHO: Malaria",
        "topic": "malaria_pregnancy",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/depression",
        "source": "who_web",
        "title": "WHO: Depression (including Perinatal)",
        "topic": "mental_health",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/pneumonia",
        "source": "who_web",
        "title": "WHO: Pneumonia in Children",
        "topic": "child_health",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/diarrhoeal-disease",
        "source": "who_web",
        "title": "WHO: Diarrhoeal Disease in Children",
        "topic": "child_health",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/immunization-coverage",
        "source": "who_web",
        "title": "WHO: Immunization Coverage",
        "topic": "immunization",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/hiv-aids",
        "source": "who_web",
        "title": "WHO: HIV/AIDS",
        "topic": "hiv_pregnancy",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/violence-against-women",
        "source": "who_web",
        "title": "WHO: Violence Against Women",
        "topic": "gender_based_violence",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/hypertension",
        "source": "who_web",
        "title": "WHO: Hypertension",
        "topic": "hypertension_pregnancy",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/diabetes",
        "source": "who_web",
        "title": "WHO: Diabetes (including Gestational)",
        "topic": "gestational_diabetes",
    },
    {
        "url": "https://www.who.int/news-room/fact-sheets/detail/tuberculosis",
        "source": "who_web",
        "title": "WHO: Tuberculosis",
        "topic": "tb_pregnancy",
    },
    # ---- UNFPA ----
    {
        "url": "https://www.unfpa.org/maternal-health",
        "source": "unfpa_web",
        "title": "UNFPA: Maternal Health",
        "topic": "maternal_health",
    },
    {
        "url": "https://www.unfpa.org/obstetric-fistula",
        "source": "unfpa_web",
        "title": "UNFPA: Obstetric Fistula",
        "topic": "obstetric_complications",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; MaternalHealthBot/1.0; "
        "public health research; +https://github.com)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_DELAY = 2       # seconds between requests — be polite
REQUEST_TIMEOUT = 20    # seconds

# -------------------------------------------------------
# Chunking constants (match the PDF pipeline)
# -------------------------------------------------------
CHUNK_SIZE   = 600   # approximate tokens
CHUNK_OVERLAP = 100
MIN_CHUNK    = 80    # approximate tokens

EMBEDDING_MODEL  = "all-MiniLM-L6-v2"
COLLECTION_NAME  = "maternal_health_minilm_v1"
CHROMA_DIR       = BASE_DIR / "data" / "chroma_db"


# -------------------------------------------------------
# Text extraction
# -------------------------------------------------------
def fetch_page(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def extract_text(html: str, url: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # Remove boilerplate
    for tag in soup.find_all(["nav", "header", "footer", "script",
                               "style", "aside", "form", "noscript",
                               "iframe", "button", "figure"]):
        tag.decompose()

    # Prefer semantic content containers
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.find("div", class_=re.compile(
            r"(content|article|fact.?sheet|body|text)", re.I
        ))
    )
    target = main if main else soup.body

    if not target:
        return ""

    # Collect text, preserving paragraph breaks
    lines = []
    for elem in target.find_all(
        ["h1", "h2", "h3", "h4", "p", "li", "td", "th", "blockquote"]
    ):
        text = elem.get_text(" ", strip=True)
        if text and len(text) > 20:
            lines.append(text)

    return "\n\n".join(lines)


# -------------------------------------------------------
# Chunking  (token-approximate: 1 token ≈ 4 chars)
# -------------------------------------------------------
def _tokens(text: str) -> int:
    return len(text) // 4


def chunk_text(text: str, url_slug: str) -> list[dict]:
    # Split on paragraph breaks first
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    chunks: list[dict] = []
    current = ""

    for para in paras:
        candidate = (current + "\n\n" + para).strip() if current else para
        if _tokens(candidate) <= CHUNK_SIZE:
            current = candidate
        else:
            if current and _tokens(current) >= MIN_CHUNK:
                chunks.append(current)
            # If the paragraph itself is too long, split on sentences
            if _tokens(para) > CHUNK_SIZE:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                buf = ""
                for sent in sentences:
                    candidate2 = (buf + " " + sent).strip() if buf else sent
                    if _tokens(candidate2) <= CHUNK_SIZE:
                        buf = candidate2
                    else:
                        if buf and _tokens(buf) >= MIN_CHUNK:
                            chunks.append(buf)
                        buf = sent
                if buf and _tokens(buf) >= MIN_CHUNK:
                    chunks.append(buf)
                current = ""
            else:
                current = para

    if current and _tokens(current) >= MIN_CHUNK:
        chunks.append(current)

    # Convert to dicts with overlap context
    result = []
    for i, chunk_text in enumerate(chunks):
        # Prepend last 100 tokens of previous chunk for context overlap
        if i > 0:
            prev = chunks[i - 1]
            overlap_chars = CHUNK_OVERLAP * 4
            prefix = prev[-overlap_chars:] if len(prev) > overlap_chars else prev
            combined = (prefix + " " + chunk_text).strip()
        else:
            combined = chunk_text

        result.append({
            "chunk_id": f"web_{url_slug}_{i:04d}",
            "text": combined,
            "metadata": {},   # filled in by caller
        })

    return result


# -------------------------------------------------------
# Main pipeline
# -------------------------------------------------------
def url_to_slug(url: str) -> str:
    slug = re.sub(r"https?://", "", url)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug)
    return slug[:80]


def run():
    import chromadb
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model...")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    logger.info("Connecting to Chroma collection...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    before = collection.count()
    logger.info(f"Collection has {before} chunks before web ingestion")

    all_chunks: list[dict] = []

    for entry in WEB_SOURCES:
        url    = entry["url"]
        source = entry["source"]
        title  = entry["title"]
        topic  = entry["topic"]
        slug   = url_to_slug(url)

        logger.info(f"Fetching: {title}")
        html = fetch_page(url)
        if not html:
            logger.warning(f"  Skipped (fetch failed): {url}")
            time.sleep(REQUEST_DELAY)
            continue

        text = extract_text(html, url)
        if not text or _tokens(text) < MIN_CHUNK * 2:
            logger.warning(f"  Skipped (insufficient text extracted): {url}")
            time.sleep(REQUEST_DELAY)
            continue

        chunks = chunk_text(text, slug)
        if not chunks:
            logger.warning(f"  Skipped (no chunks produced): {url}")
            time.sleep(REQUEST_DELAY)
            continue

        for chunk in chunks:
            chunk["metadata"] = {
                "source":    source,
                "filename":  title,
                "url":       url,
                "topic_area": topic,
                "language":  "en",
                "char_count": len(chunk["text"]),
            }

        all_chunks.extend(chunks)
        logger.info(f"  → {len(chunks)} chunks from: {title}")
        time.sleep(REQUEST_DELAY)

    if not all_chunks:
        logger.error("No chunks produced from any URL. Aborting.")
        return

    logger.info(f"Embedding {len(all_chunks)} web chunks...")
    texts = [c["text"] for c in all_chunks]
    embeddings = embedder.encode(
        texts, batch_size=32, show_progress_bar=True, convert_to_numpy=True
    )

    logger.info("Upserting into Chroma (existing PDF chunks unchanged)...")
    ids       = [c["chunk_id"] for c in all_chunks]
    documents = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]
    emb_list  = [e.tolist() for e in embeddings]

    BATCH = 200
    for i in range(0, len(all_chunks), BATCH):
        collection.upsert(
            ids=ids[i:i + BATCH],
            documents=documents[i:i + BATCH],
            embeddings=emb_list[i:i + BATCH],
            metadatas=metadatas[i:i + BATCH],
        )
        logger.info(f"  Upserted {min(i + BATCH, len(all_chunks))}/{len(all_chunks)}")

    after = collection.count()
    logger.info(
        f"Done. Collection: {before} → {after} chunks "
        f"(+{after - before} net new)"
    )

    # Save a manifest of what was ingested
    manifest_path = BASE_DIR / "data" / "web_ingestion_manifest.json"
    manifest = [
        {
            "chunk_id": c["chunk_id"],
            "url": c["metadata"]["url"],
            "title": c["metadata"]["filename"],
        }
        for c in all_chunks
    ]
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info(f"Manifest saved: {manifest_path}")


if __name__ == "__main__":
    run()
