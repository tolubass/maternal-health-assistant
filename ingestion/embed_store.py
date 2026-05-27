from pathlib import Path
from typing import List, Dict
import json
import logging
from tqdm import tqdm
import numpy as np

# Using sentence-transformers (free, runs locally, no API key needed)
from sentence_transformers import SentenceTransformer

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# -----------------------------
# Embedding Generator
# -----------------------------
class EmbeddingGenerator:
    """Generate embeddings for text chunks"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
       
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def generate_single_embedding(self, text: str) -> np.ndarray:
        
        return self.model.encode(text, convert_to_numpy=True)


# -----------------------------
# Chunk Processor
# -----------------------------
class ChunkEmbedder:
    """Process chunks and generate embeddings"""
    
    def __init__(self, embedding_generator: EmbeddingGenerator):
        self.generator = embedding_generator
    
    def load_chunks(self, chunks_file: Path) -> List[Dict]:
        """Load chunks from JSONL file"""
        logger.info(f"Loading chunks from: {chunks_file}")
        
        chunks = []
        with open(chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                chunk = json.loads(line)
                chunks.append(chunk)
        
        logger.info(f"Loaded {len(chunks)} chunks")
        return chunks
    
    def embed_chunks(self, chunks: List[Dict], batch_size: int = 32) -> List[Dict]:
        # Extract text from chunks
        texts = [chunk["text"] for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.generator.generate_embeddings(texts, batch_size=batch_size)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding.tolist()  # Convert to list for JSON serialization
        
        logger.info(f"Added embeddings to {len(chunks)} chunks")
        return chunks
    
    def save_embedded_chunks(self, chunks: List[Dict], output_file: Path):
        """Save chunks with embeddings to JSONL file"""
        logger.info(f"Saving embedded chunks to: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                json_line = json.dumps(chunk, ensure_ascii=False)
                f.write(json_line + '\n')
        
        logger.info(f"Saved {len(chunks)} embedded chunks")
    
    def save_embeddings_only(self, chunks: List[Dict], output_file: Path):
        
        embeddings = np.array([chunk["embedding"] for chunk in chunks])
        np.save(output_file, embeddings)
        logger.info(f"Saved embeddings array to: {output_file}")
        logger.info(f"Shape: {embeddings.shape}")


# -----------------------------
# Main Pipeline
# -----------------------------
def run_embedding_pipeline(
    chunks_file: Path,
    output_dir: Path,
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32
):
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize
    logger.info("Starting embedding pipeline")
    generator = EmbeddingGenerator(model_name=model_name)
    embedder = ChunkEmbedder(generator)
    
    # Load chunks
    chunks = embedder.load_chunks(chunks_file)
    
    # Generate embeddings
    embedded_chunks = embedder.embed_chunks(chunks, batch_size=batch_size)
    
    # Save outputs
    embedder.save_embedded_chunks(
        embedded_chunks, 
        output_file=output_dir / "chunks_embedded.jsonl"
    )
    
    embedder.save_embeddings_only(
        embedded_chunks,
        output_file=output_dir / "embeddings.npy"
    )
    
    # Save metadata
    metadata = {
        "num_chunks": len(chunks),
        "embedding_model": model_name,
        "embedding_dimension": generator.embedding_dim,
        "chunks_file": str(chunks_file),
        "output_dir": str(output_dir)
    }
    
    with open(output_dir / "embedding_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info("Embedding pipeline complete!")
    logger.info(f"Outputs saved to: {output_dir}")
    
    return embedded_chunks


# -----------------------------
# Main execution
# -----------------------------
if __name__ == "__main__":
    # Paths
    base_dir = Path(__file__).resolve().parents[1]
    chunks_file = base_dir / "data" / "processed" / "chunks.jsonl"
    output_dir = base_dir / "data" / "embeddings"
    
    # Check if chunks file exists
    if not chunks_file.exists():
        logger.error(f"Chunks file not found: {chunks_file}")
        logger.error("Please run chunk_text.py first to generate chunks")
        exit(1)
    
    # Run pipeline
    embedded_chunks = run_embedding_pipeline(
        chunks_file=chunks_file,
        output_dir=output_dir,
        model_name="all-MiniLM-L6-v2",  # Fast, good quality
        batch_size=32
    )
    
    logger.info(f"Successfully embedded {len(embedded_chunks)} chunks")