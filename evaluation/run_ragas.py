"""
Ragas evaluation harness for the Maternal Health Assistant.
Measures retrieval quality and generation faithfulness against a gold dataset.

Run: python evaluation/run_ragas.py
Outputs: evaluation/reports/ragas_report_<timestamp>.json
         evaluation/reports/ragas_report_<timestamp>.txt

Free setup: uses Gemini 2.5 Flash (1M tokens/day) for scoring.
No paid API required.
"""
from pathlib import Path
from datetime import datetime
import json
import os
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# -------------------------------------------------------
# Imports
# -------------------------------------------------------
try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
except ImportError as e:
    logger.error(f"Ragas import failed: {e}")
    logger.error("Run: pip install ragas datasets")
    sys.exit(1)

try:
    from datasets import Dataset
except ImportError:
    logger.error("datasets library not found. Run: pip install datasets")
    sys.exit(1)

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from ragas.llms import LangchainLLMWrapper
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
except ImportError as e:
    logger.error(f"LangChain import failed: {e}")
    logger.error("Run: pip install langchain-google-genai langchain-community")
    sys.exit(1)

import chromadb
from sentence_transformers import SentenceTransformer

# -------------------------------------------------------
# Paths
# -------------------------------------------------------
EVAL_DATASET    = ROOT / "evaluation" / "eval_dataset.jsonl"
REPORTS_DIR     = ROOT / "evaluation" / "reports"
CHROMA_DIR      = ROOT / "data" / "chroma_db"
COLLECTION      = "maternal_health_minilm_v1"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GEMINI_MODEL    = "gemini-2.5-flash"
TOP_K           = 5
MAX_DISTANCE    = 1.4
MAX_CHARS       = 800
SAMPLE_SIZE     = 5   # increase to 20 for a full run once you confirm it works

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------
# Load infrastructure
# -------------------------------------------------------
def load_infrastructure():
    logger.info("Loading embedding model...")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    logger.info("Connecting to Chroma...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION)
    logger.info(f"Collection: {collection.count()} chunks")

    return embedder, collection


def retrieve_for_question(question: str, embedder, collection) -> list[str]:
    """Return list of relevant chunk texts for a question."""
    embedding = embedder.encode(question, convert_to_numpy=True).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=TOP_K)
    texts = []
    for i, dist in enumerate(results["distances"][0]):
        if dist <= MAX_DISTANCE:
            texts.append(results["documents"][0][i][:MAX_CHARS])
    return texts if texts else [results["documents"][0][0][:MAX_CHARS]]


# -------------------------------------------------------
# Generate answers using Gemini (same model as chatbot)
# -------------------------------------------------------
def generate_answer(question: str, contexts: list[str]) -> str:
    """Generate a grounded answer using Gemini 2.5 Flash."""
    import google.generativeai as genai

    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        raise RuntimeError("GOOGLE_API_KEY not set in .env")

    genai.configure(api_key=google_key)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=(
            "You are a maternal and child health information assistant for Nigeria. "
            "Answer the question using ONLY the provided context. "
            "Cite sources using [n] markers. Use plain language."
        ),
    )

    context_text = "\n\n---\n\n".join(
        f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)
    )

    response = model.generate_content(
        f"CONTEXT:\n{context_text}\n\nQUESTION: {question}"
    )
    return response.text


# -------------------------------------------------------
# Build evaluation dataset
# -------------------------------------------------------
def build_eval_dataset(embedder, collection) -> dict:
    """
    Load gold Q&A pairs, retrieve contexts, generate answers.
    Returns dict ready for Ragas Dataset.
    """
    logger.info(f"Loading gold dataset from {EVAL_DATASET}")

    gold_pairs = []
    with open(EVAL_DATASET, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                gold_pairs.append(json.loads(line))

    # Limit sample size to control token usage
    gold_pairs = gold_pairs[:SAMPLE_SIZE]
    logger.info(f"Evaluating {len(gold_pairs)} questions (SAMPLE_SIZE={SAMPLE_SIZE})")

    questions      = []
    answers        = []
    contexts_list  = []
    ground_truths  = []

    for i, pair in enumerate(gold_pairs):
        question     = pair["question"]
        ground_truth = pair["ground_truth"]

        logger.info(f"Processing {i+1}/{len(gold_pairs)}: {question[:60]}...")

        contexts = retrieve_for_question(question, embedder, collection)
        answer   = generate_answer(question, contexts)

        questions.append(question)
        answers.append(answer)
        contexts_list.append(contexts)
        ground_truths.append(ground_truth)

    return {
        "question":     questions,
        "answer":       answers,
        "contexts":     contexts_list,
        "ground_truth": ground_truths,
    }


# -------------------------------------------------------
# Run Ragas evaluation
# -------------------------------------------------------
def run_evaluation(dataset_dict: dict) -> dict:
    """Run Ragas metrics using Gemini for scoring."""
    logger.info("Setting up Ragas with Gemini 2.5 Flash...")

    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        raise RuntimeError("GOOGLE_API_KEY not set in .env")

    # LLM for Ragas metric scoring
    gemini_llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=google_key,
        temperature=0.0,
    )
    ragas_llm = LangchainLLMWrapper(gemini_llm)

    # Embeddings for answer_relevancy metric
    hf_embeddings    = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    ragas_embeddings = LangchainEmbeddingsWrapper(hf_embeddings)

    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]

    for metric in metrics:
        metric.llm = ragas_llm
        if hasattr(metric, "embeddings"):
            metric.embeddings = ragas_embeddings

    dataset = Dataset.from_dict(dataset_dict)

    logger.info(f"Running Ragas on {len(dataset_dict['question'])} questions...")
    result = evaluate(dataset, metrics=metrics)

    return result


# -------------------------------------------------------
# Save report
# -------------------------------------------------------
def save_report(result, dataset_dict: dict):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def to_score(val):
        """Handle both scalar and list results from Ragas 0.4.x."""
        if isinstance(val, list):
            valid = [v for v in val if v is not None]
            return round(sum(valid) / len(valid), 4) if valid else 0.0
        return round(float(val), 4)

    scores = {
        "faithfulness":      to_score(result["faithfulness"]),
        "answer_relevancy":  to_score(result["answer_relevancy"]),
        "context_precision": to_score(result["context_precision"]),
        "context_recall":    to_score(result["context_recall"]),
    }

    targets = {
        "faithfulness":      {"target": "≥ 0.85", "floor": 0.75},
        "answer_relevancy":  {"target": "≥ 0.78", "floor": 0.65},
        "context_precision": {"target": "≥ 0.65", "floor": 0.50},
        "context_recall":    {"target": "≥ 0.70", "floor": 0.55},
    }

    pass_fail = {
        k: "PASS" if scores[k] >= v["floor"] else "FAIL"
        for k, v in targets.items()
    }

    report = {
        "timestamp":     timestamp,
        "sample_size":   len(dataset_dict["question"]),
        "llm_used":      GEMINI_MODEL,
        "scores":        scores,
        "targets":       targets,
        "pass_fail":     pass_fail,
    }

    # Save JSON
    json_path = REPORTS_DIR / f"ragas_report_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)

    # Save human-readable text report
    txt_path = REPORTS_DIR / f"ragas_report_{timestamp}.txt"
    lines = [
        "=" * 62,
        "MATERNAL HEALTH ASSISTANT — RAGAS EVALUATION REPORT",
        f"Timestamp   : {timestamp}",
        f"Questions   : {report['sample_size']}",
        f"LLM used    : {report['llm_used']}",
        "=" * 62,
        "",
        f"{'Metric':<25} {'Score':>8}  {'Target':>10}  {'Result':>6}",
        "-" * 62,
    ]

    for metric, score in scores.items():
        target     = targets[metric]["target"]
        result_str = pass_fail[metric]
        lines.append(f"{metric:<25} {score:>8.4f}  {target:>10}  {result_str:>6}")

    lines += [
        "",
        "=" * 62,
        "Faithfulness: fraction of answer claims supported by context.",
        "Primary hallucination metric. Floor = 0.75.",
        "=" * 62,
    ]

    with open(txt_path, "w") as f:
        f.write("\n".join(lines))

    # Print to terminal
    print("\n" + "\n".join(lines))
    logger.info(f"JSON report : {json_path}")
    logger.info(f"Text report : {txt_path}")

    return report


# -------------------------------------------------------
# Entry point
# -------------------------------------------------------
def main():
    logger.info("=== Maternal Health Assistant — Ragas Evaluation ===")
    logger.info(f"Sample size : {SAMPLE_SIZE} questions")
    logger.info(f"LLM         : {GEMINI_MODEL} (Gemini free tier)")

    embedder, collection = load_infrastructure()
    dataset_dict         = build_eval_dataset(embedder, collection)
    result               = run_evaluation(dataset_dict)
    report               = save_report(result, dataset_dict)

    all_passed = all(v == "PASS" for v in report["pass_fail"].values())
    if all_passed:
        logger.info("✅ All metrics passed their floor thresholds.")
    else:
        failed = [k for k, v in report["pass_fail"].items() if v == "FAIL"]
        logger.warning(f"⚠️  Metrics below floor: {failed}")
        logger.warning("Consider tuning retrieval or prompts before deployment.")


if __name__ == "__main__":
    main()