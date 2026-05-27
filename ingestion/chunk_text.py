from pathlib import Path
from typing import List, Dict, Optional
import re
import logging
from dataclasses import dataclass, asdict
import json

# -----------------------------
# Logging configuration
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# -----------------------------
# Configuration dataclass
# -----------------------------
@dataclass
class ChunkingConfig:
    """Configuration for text chunking parameters"""
    chunk_size: int = 600  # Target tokens per chunk
    chunk_overlap: int = 100  # Overlap between chunks
    min_chunk_size: int = 100  # Minimum chunk size to keep
    separator: str = "\n\n"  # Primary split separator
    
    def __post_init__(self):
        """Validate configuration"""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        if self.min_chunk_size > self.chunk_size:
            raise ValueError("min_chunk_size must be less than chunk_size")


# -----------------------------
# Text cleaning utilities
# -----------------------------
class TextCleaner:
    """Handles text cleaning and normalization"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and normalize text while preserving medical terminology
        
        Args:
            text: Raw text from PDF extraction
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove page numbers (common patterns)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        # Remove headers/footers (common patterns)
        text = re.sub(r'\n\s*Page \d+ of \d+\s*\n', '\n', text)
        
        # Remove excessive punctuation
        text = re.sub(r'\.{3,}', '...', text)
        
        # Clean up spaces around punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def remove_headers_footers(text: str, header_patterns: Optional[List[str]] = None) -> str:
        """
        Remove common headers and footers from documents
        
        Args:
            text: Text to clean
            header_patterns: List of regex patterns to remove
            
        Returns:
            Cleaned text
        """
        if header_patterns is None:
            header_patterns = [
                r'WHO\s+\d{4}',
                r'©\s+World Health Organization',
                r'Ministry of Health',
                r'Federal Republic of Nigeria',
            ]
        
        for pattern in header_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text


# -----------------------------
# Token counter (approximation)
# -----------------------------
class TokenCounter:
    """Approximate token counting for chunking"""
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Approximate token count (1 token ≈ 4 characters for English)
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Approximate token count
        """
        # Simple approximation: 1 token ≈ 4 characters
        # More accurate: use tiktoken library (can add later)
        return len(text) // 4
    
    @staticmethod
    def split_by_tokens(text: str, max_tokens: int) -> List[str]:
        """
        Split text into chunks by approximate token count
        
        Args:
            text: Text to split
            max_tokens: Maximum tokens per chunk
            
        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for word in words:
            word_tokens = TokenCounter.count_tokens(word)
            
            if current_tokens + word_tokens > max_tokens and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(word)
            current_tokens += word_tokens
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks


# -----------------------------
# Main chunking class
# -----------------------------
class TextChunker:
    """Handles document chunking with overlap and metadata"""
    
    def __init__(self, config: ChunkingConfig):
        self.config = config
        self.cleaner = TextCleaner()
        self.token_counter = TokenCounter()
    
    def chunk_document(self, document: Dict) -> List[Dict]:
        """
        Chunk a single document into smaller pieces
        
        Args:
            document: Document dict with 'text' and 'metadata'
            
        Returns:
            List of chunk dicts with text and metadata
        """
        text = document.get("text", "")
        metadata = document.get("metadata", {})
        
        # Clean text
        cleaned_text = self.cleaner.clean_text(text)
        cleaned_text = self.cleaner.remove_headers_footers(cleaned_text)
        
        if not cleaned_text:
            logger.warning(f"Empty text after cleaning: {metadata.get('filename', 'unknown')}")
            return []
        
        # Split into paragraphs first
        paragraphs = self._split_into_paragraphs(cleaned_text)
        
        # Create chunks with overlap
        chunks = self._create_chunks_with_overlap(paragraphs)
        
        # Create chunk documents
        chunk_documents = []
        filename = metadata.get("filename", "unknown")
        
        for idx, chunk_text in enumerate(chunks):
            chunk_id = self._generate_chunk_id(filename, idx)
            
            chunk_doc = {
                "chunk_id": chunk_id,
                "text": chunk_text,
                "metadata": {
                    **metadata,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "token_count": self.token_counter.count_tokens(chunk_text)
                }
            }
            
            chunk_documents.append(chunk_doc)
        
        return chunk_documents
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        paragraphs = text.split(self.config.separator)
        # Filter out empty paragraphs
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """
        Split a paragraph that exceeds chunk_size using a cascading separator
        strategy: tries single newline first, then falls back to word-level
        splitting. This preserves sentence coherence as much as possible
        before resorting to hard word-boundary cuts.

        Args:
            paragraph: A single paragraph string that is too large for one chunk

        Returns:
            List of sub-chunk strings, each within chunk_size
        """
        result = []

        # --- Step 1: try splitting on single newline (\n) ---
        lines = paragraph.split("\n")
        lines = [l.strip() for l in lines if l.strip()]

        if len(lines) > 1:
            # Re-group lines into chunks that respect chunk_size
            current_group = []
            current_tokens = 0

            for line in lines:
                line_tokens = self.token_counter.count_tokens(line)

                if line_tokens > self.config.chunk_size:
                    # This single line is itself too large — word-split it
                    if current_group:
                        result.append(" ".join(current_group))
                        current_group = []
                        current_tokens = 0
                    result.extend(
                        self.token_counter.split_by_tokens(line, self.config.chunk_size)
                    )
                elif current_tokens + line_tokens <= self.config.chunk_size:
                    current_group.append(line)
                    current_tokens += line_tokens
                else:
                    result.append(" ".join(current_group))
                    current_group = [line]
                    current_tokens = line_tokens

            if current_group:
                result.append(" ".join(current_group))

        else:
            # --- Step 2: no \n separators available — fall back to word-level ---
            result.extend(
                self.token_counter.split_by_tokens(paragraph, self.config.chunk_size)
            )

        return result

    def _create_chunks_with_overlap(self, paragraphs: List[str]) -> List[str]:
        """
        Create chunks from paragraphs with overlap
        
        Args:
            paragraphs: List of paragraph strings
            
        Returns:
            List of chunk strings
        """
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        i = 0
        while i < len(paragraphs):
            paragraph = paragraphs[i]
            para_tokens = self.token_counter.count_tokens(paragraph)
            
            # If single paragraph exceeds chunk size, split it
            if para_tokens > self.config.chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # ---- CHANGED: use cascading splitter instead of direct word-split ----
                sub_chunks = self._split_large_paragraph(paragraph)
                # -----------------------------------------------------------------------
                chunks.extend(sub_chunks)
                i += 1
                continue
            
            # Add paragraph to current chunk
            if current_tokens + para_tokens <= self.config.chunk_size:
                current_chunk.append(paragraph)
                current_tokens += para_tokens
                i += 1
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                
                # Create overlap
                overlap_chunk = self._create_overlap(current_chunk)
                current_chunk = overlap_chunk
                current_tokens = sum(
                    self.token_counter.count_tokens(p) for p in current_chunk
                )
        
        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        # Filter out chunks that are too small
        chunks = [
            c for c in chunks 
            if self.token_counter.count_tokens(c) >= self.config.min_chunk_size
        ]
        
        return chunks
    
    def _create_overlap(self, current_chunk: List[str]) -> List[str]:
        """
        Create overlap from end of current chunk
        
        Args:
            current_chunk: List of paragraphs in current chunk
            
        Returns:
            List of paragraphs for overlap
        """
        overlap_tokens = 0
        overlap_chunk = []
        
        # Take paragraphs from the end until we reach overlap size
        for paragraph in reversed(current_chunk):
            para_tokens = self.token_counter.count_tokens(paragraph)
            if overlap_tokens + para_tokens <= self.config.chunk_overlap:
                overlap_chunk.insert(0, paragraph)
                overlap_tokens += para_tokens
            else:
                break
        
        return overlap_chunk
    
    def _generate_chunk_id(self, filename: str, index: int) -> str:
        """
        Generate unique chunk ID
        
        Args:
            filename: Source filename
            index: Chunk index
            
        Returns:
            Unique chunk ID
        """
        # Remove file extension and sanitize
        base_name = Path(filename).stem
        base_name = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)
        return f"{base_name}_{index:04d}"


# -----------------------------
# Document processor
# -----------------------------
class DocumentProcessor:
    """Process multiple documents and save chunks"""
    
    def __init__(self, config: ChunkingConfig, output_dir: Path):
        self.chunker = TextChunker(config)
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Process all documents and create chunks
        
        Args:
            documents: List of document dicts
            
        Returns:
            List of all chunks
        """
        all_chunks = []
        
        logger.info(f"Processing {len(documents)} documents")
        
        for doc in documents:
            filename = doc.get("metadata", {}).get("filename", "unknown")
            logger.info(f"Chunking: {filename}")
            
            try:
                chunks = self.chunker.chunk_document(doc)
                all_chunks.extend(chunks)
                logger.info(f"  Created {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"  Failed to chunk {filename}: {e}")
        
        logger.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks
    
    def save_chunks(self, chunks: List[Dict], filename: str = "chunks.jsonl"):
        """
        Save chunks to JSONL file
        
        Args:
            chunks: List of chunk dicts
            filename: Output filename
        """
        output_path = self.output_dir / filename
        
        logger.info(f"Saving chunks to: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                json_line = json.dumps(chunk, ensure_ascii=False)
                f.write(json_line + '\n')
        
        logger.info(f"Successfully saved {len(chunks)} chunks")
        
        # Save statistics
        self._save_statistics(chunks)
    
    def _save_statistics(self, chunks: List[Dict]):
        """Save chunking statistics"""
        stats_path = self.output_dir / "chunking_stats.json"
        
        token_counts = [c["metadata"]["token_count"] for c in chunks]
        
        stats = {
            "total_chunks": len(chunks),
            "total_documents": len(set(c["metadata"]["filename"] for c in chunks)),
            "avg_tokens_per_chunk": sum(token_counts) / len(token_counts) if token_counts else 0,
            "min_tokens": min(token_counts) if token_counts else 0,
            "max_tokens": max(token_counts) if token_counts else 0,
        }
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Statistics: {stats}")


# -----------------------------
# Main execution
# -----------------------------
if __name__ == "__main__":
    from load_pdfs import PDFLoader
    
    # Paths
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data" / "raw"
    output_dir = base_dir / "data" / "processed"
    
    # Load PDFs
    logger.info("Loading PDFs...")
    loader = PDFLoader(data_dir=data_dir)
    documents = loader.load_pdfs()
    
    # Configure chunking
    config = ChunkingConfig(
        chunk_size=600,
        chunk_overlap=100,
        min_chunk_size=100
    )
    
    # Process and save chunks
    processor = DocumentProcessor(config=config, output_dir=output_dir)
    chunks = processor.process_documents(documents)
    processor.save_chunks(chunks)
    
    logger.info("Chunking complete!")