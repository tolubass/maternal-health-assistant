# Maternal Health Assistant

A retrieval-augmented generation (RAG) chatbot that answers maternal and child health questions using authoritative guidelines from WHO, the Nigerian Federal Ministry of Health (FMOH), NPHCDA, UNICEF, and NCDC.

Built for pregnant women, new mothers, caregivers, and community health workers in Nigeria.

---

## Features

- **Evidence-based answers** — every response is grounded in official health guidelines, with numbered source citations
- **Four-layer safety stack** — emergency detection, input filtering, output validation, and hardcoded fallback responses
- **Dual-LLM strategy** — Google Gemini 2.5 Flash (primary) with automatic fallback to Groq Llama 3.3 70B
- **Conversation memory** — maintains context across turns; handles "continue", "tell me more", and other follow-up phrases
- **Multi-page React UI** — Home, Chat, and FAQ pages with a professional blue design
- **Nigeria-first** — knowledge base drawn from Nigeria-specific health policy documents and WHO guidelines adapted for the Nigerian context

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.10+) |
| LLM (primary) | Google Gemini 2.5 Flash |
| LLM (fallback) | Groq — Llama 3.3 70B Versatile |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers) |
| Vector store | ChromaDB (persistent) |
| Frontend | React 19 + Vite 8 |
| Routing | react-router-dom v7 |
| Containerization | Docker + Docker Compose |
| Deployment | Render (free tier) |

---

## Project Structure

```
maternal-health-assistant/
├── app/
│   └── main.py               # FastAPI app, endpoints, LLM calls
├── safety/
│   └── __init__.py           # Four-layer safety pipeline
├── ingestion/
│   ├── load_pdfs.py          # PDF text extraction
│   ├── chunk_text.py         # Text chunking
│   ├── embed_store.py        # Embedding + Chroma storage
│   ├── build_chroma.py       # Build the vector DB
│   ├── run_ingestion.py      # Full ingestion pipeline runner
│   └── scrape_web.py         # Web source scraper
├── frontend/
│   ├── src/
│   │   ├── pages/            # HomePage, ChatPage, FAQPage
│   │   ├── components/       # Navbar, Footer, ChatWindow, etc.
│   │   ├── hooks/useChat.js  # Chat state and API logic
│   │   ├── services/api.js   # Fetch wrapper
│   │   ├── App.jsx           # Router + routes
│   │   └── index.css         # Global styles + design tokens
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── data/
│   ├── chroma_db/            # Committed vector DB (baked into Docker image)
│   └── raw/                  # Source PDFs (gitignored — add your own)
├── tests/                    # Pytest unit tests
├── scripts/
│   ├── reingest.ps1          # Re-run ingestion pipeline
│   └── promote_release.ps1   # Tag and push a versioned release
├── Dockerfile
├── docker-compose.yml
├── versions.json
├── .env.example
└── requirements.txt
```

---

## Local Setup

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- A Google AI Studio API key (Gemini) and/or a Groq API key

### 1. Clone the repository

```bash
git clone https://github.com/tolubass/maternal-health-assistant.git
cd maternal-health-assistant
```

### 2. Create and activate a Python environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```env
GOOGLE_API_KEY=your_google_ai_studio_key
GROQ_API_KEY=your_groq_api_key
CORS_ORIGINS=http://localhost:5173
```

At least one of `GOOGLE_API_KEY` or `GROQ_API_KEY` is required.

### 5. Install frontend dependencies and build (or run dev server)

```bash
cd frontend
npm install

# Development (hot reload, proxies API to localhost:8000)
npm run dev

# Production build
npm run build
cd ..
```

### 6. Start the API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The app is now available at `http://localhost:8000` (production build) or `http://localhost:5173` (Vite dev server).

---

## Running with Docker

```bash
# Build and start
docker compose up --build

# Stop
docker compose down
```

The Docker image bakes the pre-built Chroma vector DB into the image so no ingestion step is needed at startup.

---

## API Reference

### `GET /health`

Liveness check. Returns collection size and LLM availability.

```json
{
  "status": "ok",
  "collection_size": 2406,
  "gemini_available": true,
  "groq_available": true
}
```

### `POST /chat`

Ask a maternal health question.

**Request body:**

```json
{
  "question": "What are the danger signs during pregnancy?",
  "history": [
    { "role": "user",      "content": "How many antenatal visits do I need?" },
    { "role": "assistant", "content": "WHO recommends a minimum of eight..." }
  ]
}
```

**Response:**

```json
{
  "answer": "The danger signs during pregnancy include...",
  "citations": [
    { "index": 1, "source": "WHO ANC Guidelines", "filename": "who-recommendations-antenatal-care.pdf" }
  ]
}
```

`history` is optional. When provided, it enables multi-turn conversation and follow-up handling.

---

## Safety Architecture

Every question passes through four sequential layers before a response is returned:

| Layer | What it does |
|---|---|
| **1. Emergency detection** | Pattern-matches on symptoms like heavy bleeding, convulsions, loss of consciousness. Returns a hardcoded "go to the nearest health facility immediately" response — no LLM involved. |
| **2. Input filter** | Blocks requests for specific diagnoses, medication dosages, and completely off-topic queries. Returns a category-specific refusal message. |
| **3. Retrieval + Generation** | Embeds the question, retrieves the top-K relevant chunks from Chroma, and prompts the LLM to answer from the retrieved context only. Falls back to Groq if Gemini fails. |
| **4. Output validation** | Scans the LLM response for prohibited content (diagnosis, prescription, harmful advice). Replaces the response with a safe fallback if violations are found. |

---

## Re-ingesting the Knowledge Base

If you add new PDFs to `data/raw/`, re-run the full pipeline:

```powershell
# Windows — runs PDF ingestion + web scraping
.\scripts\reingest.ps1

# PDF ingestion only
.\scripts\reingest.ps1 -PdfOnly

# Web scraping only
.\scripts\reingest.ps1 -WebOnly
```

After re-ingestion, commit the updated `data/chroma_db/` before deploying:

```bash
git add data/chroma_db/
git commit -m "data: update chroma_db after re-ingestion"
git push origin main
```

---

## Deployment to Render

1. Fork or push this repository to GitHub.
2. Create a new **Web Service** on [Render](https://render.com).
3. Connect your GitHub repository.
4. Set the following environment variables in the Render dashboard:
   - `GOOGLE_API_KEY`
   - `GROQ_API_KEY`
   - `CORS_ORIGINS` (set to your Render service URL, e.g. `https://your-app.onrender.com`)
5. Render will automatically build using the `Dockerfile` and deploy.

> **Note:** The free tier has no persistent disk. The Chroma vector DB is committed to the repository and baked directly into the Docker image at build time — no separate setup required.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Knowledge Sources

The knowledge base is built from official documents including:

- **WHO** — ANC guidelines, childbirth recommendations, IMNCI, infant feeding counselling
- **Nigerian FMOH** — Integrated Maternal, Newborn and Child Health Strategy, National Child Health Policy
- **NPHCDA** — National immunization schedule, primary health care standards
- **UNICEF** — Infant and young child feeding policy, Nigeria equity health profile
- **NCDC** — Infection prevention and control, IMCI reference manual

---

## License

This project is for informational and educational purposes. It is not a substitute for professional medical advice. Users experiencing a medical emergency should call **112** or go to the nearest health facility immediately.
