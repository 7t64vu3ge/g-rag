import uvicorn
from dotenv import load_dotenv

# Load .env before any module that reads environment variables
load_dotenv()

from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="RAG Backend",
    description="Retrieval-Augmented Generation API backed by Google Drive, FAISS, and Groq.",
    version="1.0.0",
)

app.include_router(router)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
