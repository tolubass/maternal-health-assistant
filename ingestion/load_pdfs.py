from pathlib import Path
from typing import List, Dict
from pypdf import PdfReader
import logging

# -----------------------------
# Logging configuration
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# -----------------------------
# Core PDF loader
# -----------------------------
class PDFLoader:
    def __init__(self, data_dir: Path):
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory does not exist: {data_dir}")
        self.data_dir = data_dir

    def load_pdfs(self) -> List[Dict]:
        documents = []

        pdf_files = list(self.data_dir.rglob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files")

        for pdf_path in pdf_files:
            try:
                logger.info(f"Loading: {pdf_path.name}")
                reader = PdfReader(pdf_path)

                text_pages = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    text_pages.append(page_text)

                full_text = "\n".join(text_pages)

                document = {
                    "text": full_text,
                    "metadata": {
                        "filename": pdf_path.name,
                        "source": pdf_path.parent.name,
                        "path": str(pdf_path),
                        "num_pages": len(reader.pages),
                        "num_characters": len(full_text)
                    }
                }

                documents.append(document)

            except Exception as e:
                logger.error(f"Failed to load {pdf_path.name}: {e}")

        logger.info(f"Successfully loaded {len(documents)} documents")
        return documents 


# -----------------------------
# Local test execution
# -----------------------------
if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data" / "raw"

    loader = PDFLoader(data_dir=data_dir)
    docs = loader.load_pdfs()

    for doc in docs:
        meta = doc["metadata"]
        logger.info(
            f"Loaded {meta['filename']} | "
            f"Pages: {meta['num_pages']} | "
            f"Chars: {meta['num_characters']}"
        )
