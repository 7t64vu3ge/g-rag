# RAG Backend

A modular Retrieval-Augmented Generation (RAG) backend built with FastAPI. Syncs documents from Google Drive, processes and indexes them using FAISS, and answers natural-language queries via the Groq LLM.

## Architecture

```
project/
├── connectors/
│   └── gdrive.py          # Google Drive API integration
├── processing/
│   ├── loader.py           # PDF, TXT, Google Docs text extraction
│   └── chunker.py          # Word-based text chunking with overlap
├── embedding/
│   └── embedder.py         # SentenceTransformer embeddings
├── search/
│   ├── vector_store.py     # FAISS index storage
│   └── retriever.py        # Query embedding + vector search
├── api/
│   └── routes.py           # FastAPI route definitions
├── main.py                 # App entry point
├── requirements.txt
├── .env                    # API keys and config (not committed)
└── service_account.json    # Google service account credentials (not committed)
```

## Prerequisites

- Python 3.9+
- A Google Cloud service account with Drive API enabled
- A Groq API key

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd project
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=service_account.json
GDRIVE_FOLDER_ID=your_google_drive_folder_id_here
```

### 3. Add Google service account credentials

Place your service account JSON file at the path specified in `GOOGLE_APPLICATION_CREDENTIALS` (default: `service_account.json`).

**IMPORTANT**: The service account needs **Viewer** access to your target Google Drive folder. 
1. Copy the `client_email` from your JSON file.
2. Go to your Google Drive folder, click **Share**, and invite that email as a **Viewer**.

### 4. Run the server

```bash
python main.py
```

The API will be available at `http://localhost:8000`.

Interactive docs: `http://localhost:8000/docs`

## API Endpoints

### `GET /config`

Returns the current configuration, including the service account email and target folder ID. Use this to verify setup.

```bash
curl http://localhost:8000/config
```

### `POST /sync-drive`

Fetches all supported files from the configured Google Drive folder, processes them, and indexes them in FAISS.

```bash
curl -X POST http://localhost:8000/sync-drive
```

**Response:**
```json
{
  "synced": 3,
  "chunks_added": 142
}
```

### `POST /ask`

Answers a natural-language question using the indexed documents as context.

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the refund policy?"}'
```

**Response:**
```json
{
  "answer": "The refund policy allows returns within 30 days of purchase...",
  "sources": ["policy.pdf", "faq.txt"]
}
```

If the answer is not found in the indexed documents:
```json
{
  "answer": "Not found in documents",
  "sources": []
}
```

## Supported File Types

| Type | MIME Type | Processing |
|------|-----------|------------|
| PDF | `application/pdf` | PyMuPDF text extraction |
| Plain Text | `text/plain` | UTF-8 read |
| Google Docs | `application/vnd.google-apps.document` | Exported as plain text |

## Data Flow

```
POST /sync-drive
  └── GDrive Connector  →  list + download files
        └── Loader       →  extract raw text
              └── Chunker  →  split into 400-word chunks (50-word overlap)
                    └── Embedder  →  encode with all-MiniLM-L6-v2
                          └── Vector Store  →  add to FAISS index

POST /ask
  └── Embedder      →  embed query
        └── Retriever  →  top-5 FAISS search
              └── Groq LLM  →  answer from context (llama-3.3-70b-versatile)
                    └── Response  →  { answer, sources }
```

## Configuration Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq API key | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | Yes |
| `GDRIVE_FOLDER_ID` | Google Drive folder ID to sync from | Yes |

## Tech Stack

- **FastAPI** — HTTP framework
- **SentenceTransformers** (`all-MiniLM-L6-v2`) — text embeddings
- **FAISS** (`IndexFlatL2`) — vector similarity search
- **PyMuPDF** — PDF text extraction
- **Groq** (`llama-3.3-70b-versatile`) — LLM for answer generation
- **Google Drive API** — document source
