import logging
import os

from fastapi import APIRouter
from groq import Groq
from pydantic import BaseModel, field_validator

from connectors.gdrive import fetch_files
from embedding.embedder import embed_texts
from processing.chunker import chunk_text
from processing.loader import extract_text
from search import vector_store
from search.retriever import retrieve

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Groq client — initialised once; fails fast if key is missing
# ---------------------------------------------------------------------------
_groq_api_key = os.environ.get("GROQ_API_KEY")
if not _groq_api_key:
    raise EnvironmentError(
        "GROQ_API_KEY environment variable is not set. "
        "Provide a valid Groq API key before starting the server."
    )

_groq_client = Groq(api_key=_groq_api_key)

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question using ONLY the "
    "context provided below. If the context does not contain enough information "
    "to answer the question, respond with exactly: Not found in documents\n\n"
    "Context:\n{context}"
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()


class AskResponse(BaseModel):
    answer: str
    sources: list[str]


class SyncResponse(BaseModel):
    synced: int
    chunks_added: int


class ConfigResponse(BaseModel):
    service_account_email: str
    folder_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/")
def root():
    """
    Root endpoint providing basic instructions.
    """
    return {
        "message": "Welcome to the RAG Backend!",
        "instructions": (
            "1. Share your Google Drive folder with the service account email found at /config or /info. "
            "2. Run /sync-drive to index your documents. "
            "3. Ask questions using /ask."
        ),
        "docs": "/docs"
    }


@router.get("/config", response_model=ConfigResponse)
@router.get("/info", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    """
    Return the service account email and target folder ID to help with setup.
    """
    import json
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    email = "Unknown"
    if creds_path and os.path.exists(creds_path):
        with open(creds_path, "r") as f:
            data = json.load(f)
            email = data.get("client_email", "Unknown")

    return ConfigResponse(
        service_account_email=email,
        folder_id=os.environ.get("GDRIVE_FOLDER_ID", "Not set")
    )


@router.post("/sync-drive", response_model=SyncResponse)
def sync_drive() -> SyncResponse:
    """
    Fetch all supported files from Google Drive, process them, and index
    their content in the FAISS vector store.
    """
    synced = 0
    chunks_added = 0

    for file_info in fetch_files():
        file_name = file_info["file_name"]
        doc_id = file_info["doc_id"]
        mime_type = file_info["mime_type"]
        content = file_info["content"]

        try:
            text = extract_text(content, mime_type, file_name)
            if not text:
                logger.warning("'%s' produced no text — skipping.", file_name)
                continue

            chunks = chunk_text(text)
            if not chunks:
                logger.warning("'%s' produced no chunks — skipping.", file_name)
                continue

            embeddings = embed_texts(chunks)
            metadata = [
                {"file_name": file_name, "doc_id": doc_id, "source": "gdrive"}
                for _ in chunks
            ]

            vector_store.add(chunks, embeddings, metadata)
            synced += 1
            chunks_added += len(chunks)
            logger.info("Indexed '%s': %d chunk(s).", file_name, len(chunks))

        except Exception as exc:
            logger.error("Failed to process '%s': %s", file_name, exc)
            continue

    return SyncResponse(synced=synced, chunks_added=chunks_added)


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """
    Answer a natural-language query using the indexed documents as context.
    """
    results = retrieve(request.query, k=5)

    if not results:
        return AskResponse(answer="Not found in documents", sources=[])

    context = "\n\n".join(r["text"] for r in results)
    sources = list({r["meta"]["file_name"] for r in results})

    completion = _groq_client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(context=context),
            },
            {
                "role": "user",
                "content": request.query,
            },
        ],
    )

    answer = completion.choices[0].message.content.strip()
    return AskResponse(answer=answer, sources=sources)
