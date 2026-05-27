"""
Full ingestion pipeline orchestrator.

Steps:
  1. load_pdfs    — extract text from data/raw/**/*.pdf
  2. chunk_text   — split into 600-token chunks with 100-token overlap
  3. enrich       — add topic_area, char_count, language to metadata
  4. validate     — assert required fields, minimum token count, no duplicates
  5. embed_store  — generate all-MiniLM-L6-v2 embeddings
  6. build_chroma — upsert into persistent Chroma collection

Run from project root:
    python ingestion/run_ingestion.py

On success the Chroma DB at data/chroma_db/ is ready to serve queries.
"""
from pathlib import Path
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))


def step_load_pdfs() -> list[dict]:
    from ingestion.load_pdfs import PDFLoader
    loader = PDFLoader(data_dir=BASE_DIR / "data" / "raw")
    docs = loader.load_pdfs()
    if not docs:
        raise RuntimeError("No PDFs loaded — check data/raw/ directory")
    logger.info(f"Step 1 complete: {len(docs)} PDFs loaded")
    return docs


def step_chunk(docs: list[dict]) -> int:
    from ingestion.chunk_text import DocumentProcessor, ChunkingConfig
    out_dir = BASE_DIR / "data" / "processed"
    config = ChunkingConfig(chunk_size=600, overlap=100, min_chunk_size=100)
    processor = DocumentProcessor(config=config, output_dir=out_dir)
    chunks = processor.process_documents(docs)
    processor.save_chunks(chunks, "chunks.jsonl")
    logger.info(f"Step 2 complete: {len(chunks)} chunks created")
    return len(chunks)


def step_enrich() -> int:
    from ingestion.enrich_metadata import enrich
    count = enrich()
    logger.info(f"Step 3 complete: {count} chunks enriched")
    return count


def step_validate() -> None:
    from ingestion.validate_chunks import validate
    ok = validate()
    if not ok:
        raise RuntimeError("Chunk validation failed — fix errors before embedding")
    logger.info("Step 4 complete: validation passed")


def step_embed() -> None:
    from ingestion.embed_store import run_embedding_pipeline
    run_embedding_pipeline(
        chunks_file=BASE_DIR / "data" / "processed" / "chunks.jsonl",
        output_dir=BASE_DIR / "data" / "embeddings",
        model_name="all-MiniLM-L6-v2",
        batch_size=32,
    )
    logger.info("Step 5 complete: embeddings generated")


def step_build_chroma() -> None:
    from ingestion.build_chroma import main as build_chroma_main
    build_chroma_main()
    logger.info("Step 6 complete: Chroma DB built")


def main() -> None:
    logger.info("=== Maternal Health Ingestion Pipeline ===")

    try:
        docs = step_load_pdfs()
        step_chunk(docs)
        step_enrich()
        step_validate()
        step_embed()
        step_build_chroma()
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

    logger.info("=== Pipeline complete. data/chroma_db/ is ready. ===")


if __name__ == "__main__":
    main()
