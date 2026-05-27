# -------------------------------------------------------
# Stage 1: Build React frontend
# -------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ .
RUN npm run build

# -------------------------------------------------------
# Stage 2: Python API server
# -------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first to keep the image smaller (~500 MB vs ~2 GB)
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so startup on Render is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
# Verify new Gemini SDK is importable
RUN python -c "from google import genai; from google.genai import types; print('Gemini SDK OK')"

# Copy application source
COPY app/ app/
COPY safety/ safety/

# Copy pre-built vector database (committed to git, see .gitignore)
COPY data/chroma_db/ data/chroma_db/

# Copy React production build from Stage 1
COPY --from=frontend-builder /frontend/dist frontend/dist/

# Render injects PORT; fall back to 8000 locally
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
