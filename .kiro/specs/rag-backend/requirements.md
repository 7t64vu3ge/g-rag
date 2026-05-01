# Requirements Document

## Introduction

This document defines the requirements for a RAG (Retrieval-Augmented Generation) backend built with FastAPI. The system syncs documents from Google Drive using a service account, processes PDF, TXT, and Google Docs files, chunks and embeds the text using SentenceTransformers, stores vectors in FAISS, and answers natural-language queries by retrieving relevant context and passing it to the Groq LLM.

The architecture is strictly modular:

```
project/
  connectors/gdrive.py
  processing/loader.py
  processing/chunker.py
  embedding/embedder.py
  search/vector_store.py
  search/retriever.py
  api/routes.py
  main.py
```

---

## Glossary

- **System**: The RAG backend FastAPI application as a whole.
- **GDrive_Connector**: The module (`connectors/gdrive.py`) responsible for authenticating with Google Drive and fetching files.
- **Loader**: The module (`processing/loader.py`) responsible for extracting raw text from supported file types.
- **Chunker**: The module (`processing/chunker.py`) responsible for splitting text into overlapping word-based chunks.
- **Embedder**: The module (`embedding/embedder.py`) responsible for producing vector embeddings from text using SentenceTransformers.
- **Vector_Store**: The module (`search/vector_store.py`) responsible for storing and searching embeddings using FAISS.
- **Retriever**: The module (`search/retriever.py`) responsible for orchestrating query embedding and vector search to return relevant chunks.
- **Router**: The module (`api/routes.py`) that defines the FastAPI HTTP endpoints.
- **LLM_Client**: The Groq SDK client used to generate answers from retrieved context.
- **Service_Account**: A Google Cloud service account JSON credential file used for Drive API authentication.
- **Chunk**: A fixed-size, overlapping segment of text derived from a source document.
- **Embedding**: A 384-dimensional float32 vector representation of a text chunk or query produced by the `all-MiniLM-L6-v2` model.
- **Sync**: The process of fetching files from Google Drive, loading, chunking, embedding, and storing them in the Vector_Store.

---

## Requirements

### Requirement 1: Google Drive Authentication

**User Story:** As a system operator, I want the backend to authenticate with Google Drive using a service account, so that it can access files without user interaction.

#### Acceptance Criteria

1. THE GDrive_Connector SHALL authenticate with the Google Drive API using a Service_Account JSON credential file whose path is provided via the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.
2. THE GDrive_Connector SHALL request the `https://www.googleapis.com/auth/drive.readonly` OAuth scope during authentication.
3. IF the Service_Account credential file is missing or invalid, THEN THE GDrive_Connector SHALL raise a descriptive exception that includes the file path and the reason for failure.

---

### Requirement 2: Google Drive File Fetching

**User Story:** As a system operator, I want the backend to list and download supported files from Google Drive, so that their content can be processed and indexed.

#### Acceptance Criteria

1. WHEN the `/sync-drive` endpoint is called, THE GDrive_Connector SHALL list all files in the configured Google Drive folder whose MIME type is one of: `application/pdf`, `text/plain`, or `application/vnd.google-apps.document`.
2. WHEN a file of MIME type `application/pdf` or `text/plain` is fetched, THE GDrive_Connector SHALL download the binary content of the file.
3. WHEN a file of MIME type `application/vnd.google-apps.document` is fetched, THE GDrive_Connector SHALL export the file content as `text/plain`.
4. THE GDrive_Connector SHALL return, for each file, the file name, the Google Drive file ID, and the downloaded content.
5. IF the Google Drive API returns an error during listing or downloading, THEN THE GDrive_Connector SHALL raise a descriptive exception that includes the file ID and the HTTP status code.

---

### Requirement 3: Document Text Extraction

**User Story:** As a developer, I want the backend to extract plain text from each supported file type, so that the content can be chunked and embedded.

#### Acceptance Criteria

1. WHEN a PDF file is provided, THE Loader SHALL extract all text from every page using PyMuPDF and return it as a single string.
2. WHEN a TXT file is provided, THE Loader SHALL read the file using UTF-8 encoding and return its full content as a string.
3. WHEN a Google Docs file is provided as exported plain text, THE Loader SHALL return the content as a string without additional transformation.
4. WHEN extracted text contains leading or trailing whitespace, THE Loader SHALL strip that whitespace before returning the string.
5. IF a PDF file is corrupt or unreadable by PyMuPDF, THEN THE Loader SHALL raise a descriptive exception that includes the file name.

---

### Requirement 4: Text Chunking

**User Story:** As a developer, I want the backend to split documents into overlapping word-based chunks, so that embeddings capture focused, context-rich segments.

#### Acceptance Criteria

1. WHEN text is provided to the Chunker, THE Chunker SHALL split the text into chunks of at most 400 words each.
2. WHEN producing consecutive chunks, THE Chunker SHALL apply an overlap of 50 words between adjacent chunks.
3. WHEN text contains fewer than 400 words, THE Chunker SHALL return a single chunk containing all words.
4. THE Chunker SHALL return a list of non-empty strings, where each string is a space-joined sequence of words.
5. FOR ALL input texts, the union of all words across all chunks produced by the Chunker SHALL contain every word from the original text (coverage property).

---

### Requirement 5: Text Embedding

**User Story:** As a developer, I want the backend to produce vector embeddings for text chunks and queries, so that semantic similarity search is possible.

#### Acceptance Criteria

1. THE Embedder SHALL load the `all-MiniLM-L6-v2` SentenceTransformer model once at module initialisation.
2. WHEN a list of text strings is provided, THE Embedder SHALL encode all strings in a single batch call and return a list of 384-dimensional float32 vectors.
3. WHEN a single query string is provided, THE Embedder SHALL return a single 384-dimensional float32 vector.
4. FOR ALL input text lists, the number of embeddings returned by the Embedder SHALL equal the number of input strings (length-preservation property).

---

### Requirement 6: Vector Storage

**User Story:** As a developer, I want the backend to store embeddings alongside their source chunks and metadata in FAISS, so that fast nearest-neighbour search is available at query time.

#### Acceptance Criteria

1. THE Vector_Store SHALL initialise a `faiss.IndexFlatL2` index with dimension 384 at module load time.
2. WHEN `add()` is called with a list of chunks, a corresponding list of embeddings, and a corresponding list of metadata dicts, THE Vector_Store SHALL add the embeddings to the FAISS index and store the chunks and metadata in parallel in-memory lists.
3. WHEN `search()` is called with a query embedding and a value `k`, THE Vector_Store SHALL return the `k` nearest chunks as a list of dicts, each containing the keys `"text"` and `"meta"`.
4. THE Vector_Store `add()` function SHALL accept metadata dicts that contain at minimum the keys `"file_name"`, `"doc_id"`, and `"source"`.
5. IF `search()` is called when the index contains fewer than `k` entries, THEN THE Vector_Store SHALL return all available entries without raising an exception.

---

### Requirement 7: Document Metadata

**User Story:** As a developer, I want every stored chunk to carry structured metadata, so that query responses can cite their sources accurately.

#### Acceptance Criteria

1. WHEN a chunk is stored in the Vector_Store, THE System SHALL attach a metadata dict containing the key `"file_name"` set to the original file name, the key `"doc_id"` set to the Google Drive file ID, and the key `"source"` set to the string `"gdrive"`.
2. WHEN the `/ask` endpoint returns an answer, THE System SHALL include in the `"sources"` field the distinct `"file_name"` values from all retrieved chunks used to construct the answer.

---

### Requirement 8: Retrieval Orchestration

**User Story:** As a developer, I want a dedicated retriever module to coordinate query embedding and vector search, so that the API layer stays thin and retrieval logic is reusable.

#### Acceptance Criteria

1. WHEN `retrieve()` is called with a query string and an optional `k` parameter (default 5), THE Retriever SHALL embed the query using the Embedder and pass the resulting vector to the Vector_Store `search()` function.
2. THE Retriever SHALL return the list of result dicts produced by the Vector_Store unchanged.
3. THE Retriever SHALL not perform any LLM calls or HTTP requests.

---

### Requirement 9: Sync Endpoint

**User Story:** As a system operator, I want a `/sync-drive` endpoint, so that I can trigger document ingestion from Google Drive on demand.

#### Acceptance Criteria

1. THE Router SHALL expose a `POST /sync-drive` endpoint that accepts no request body.
2. WHEN `POST /sync-drive` is called, THE System SHALL fetch all supported files from Google Drive, extract text from each file, chunk each text, embed all chunks, and store the embeddings and metadata in the Vector_Store.
3. WHEN `POST /sync-drive` completes successfully, THE Router SHALL return a JSON response with the key `"synced"` set to the integer count of files processed.
4. IF an error occurs during sync for any individual file, THEN THE System SHALL log the file name and error message and continue processing the remaining files.
5. WHEN `POST /sync-drive` completes, THE Router SHALL include in the response the key `"chunks_added"` set to the total integer count of chunks stored across all processed files.

---

### Requirement 10: Query Endpoint

**User Story:** As an end user, I want a `/ask` endpoint, so that I can ask natural-language questions and receive answers grounded in the indexed documents.

#### Acceptance Criteria

1. THE Router SHALL expose a `POST /ask` endpoint that accepts a JSON body with the key `"query"` containing a non-empty string.
2. WHEN `POST /ask` is called, THE System SHALL embed the query, retrieve the top-5 most relevant chunks from the Vector_Store, and send the concatenated chunk texts as context to the LLM_Client.
3. WHEN sending context to the LLM_Client, THE System SHALL use the Groq model `llama3-8b-8192` with `temperature=0`.
4. THE System SHALL instruct the LLM_Client via the system prompt to answer only using the provided context and to respond with `"Not found in documents"` when the context does not contain a relevant answer.
5. WHEN `POST /ask` returns a response, THE Router SHALL return a JSON object with the key `"answer"` set to the LLM_Client's response text and the key `"sources"` set to a list of distinct file names from the retrieved chunks.
6. IF the `"query"` field is missing or empty, THEN THE Router SHALL return HTTP 422 with a descriptive validation error.
7. THE LLM_Client SHALL be initialised using the `GROQ_API_KEY` environment variable.
8. IF the `GROQ_API_KEY` environment variable is not set, THEN THE System SHALL raise a descriptive exception at startup.

---

### Requirement 11: Application Entry Point

**User Story:** As a developer, I want a `main.py` entry point that wires all modules together and starts the FastAPI server, so that the application can be launched with a single command.

#### Acceptance Criteria

1. THE System SHALL define a FastAPI application instance in `main.py` and register the Router from `api/routes.py`.
2. WHEN `main.py` is executed directly, THE System SHALL start the Uvicorn server on host `0.0.0.0` and port `8000`.
3. THE System SHALL load environment variables from a `.env` file at startup if one is present, using `python-dotenv`.

---

### Requirement 12: Dependency Specification

**User Story:** As a developer, I want a complete `requirements.txt`, so that the environment can be reproduced exactly.

#### Acceptance Criteria

1. THE System's `requirements.txt` SHALL include pinned or minimum-version entries for: `fastapi`, `uvicorn`, `sentence-transformers`, `faiss-cpu`, `pymupdf`, `groq`, `google-api-python-client`, `google-auth`, `python-dotenv`, and `pydantic`.
2. THE System's `requirements.txt` SHALL NOT include packages unrelated to the application's runtime dependencies.
