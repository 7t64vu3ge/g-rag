import io
import os
import logging
from typing import Generator

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

SUPPORTED_MIME_TYPES = [
    "application/pdf",
    "text/plain",
    "application/vnd.google-apps.document",
]

GDOCS_MIME = "application/vnd.google-apps.document"


def _build_service():
    """Authenticate and return a Google Drive API service client."""
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"Service account credentials not found at '{creds_path}'. "
            "Set the GOOGLE_APPLICATION_CREDENTIALS environment variable to a valid path."
        )
    try:
        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )
    except Exception as exc:
        raise ValueError(
            f"Failed to load service account credentials from '{creds_path}': {exc}"
        ) from exc

    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _list_files(service, folder_id: str) -> list[dict]:
    """List all supported files in the given Drive folder."""
    mime_filter = " or ".join(
        [f"mimeType='{m}'" for m in SUPPORTED_MIME_TYPES]
    )
    query = f"'{folder_id}' in parents and ({mime_filter}) and trashed=false"

    files = []
    page_token = None

    while True:
        try:
            response = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                )
                .execute()
            )
        except HttpError as exc:
            raise RuntimeError(
                f"Google Drive API error while listing files in folder '{folder_id}': "
                f"HTTP {exc.resp.status} — {exc}"
            ) from exc

        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return files


def _download_file(service, file_id: str, mime_type: str) -> bytes:
    """Download or export a file and return its raw bytes."""
    try:
        if mime_type == GDOCS_MIME:
            request = service.files().export_media(
                fileId=file_id, mimeType="text/plain"
            )
        else:
            request = service.files().get_media(fileId=file_id)

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        return buffer.getvalue()

    except HttpError as exc:
        raise RuntimeError(
            f"Google Drive API error while downloading file '{file_id}': "
            f"HTTP {exc.resp.status} — {exc}"
        ) from exc


def fetch_files() -> Generator[dict, None, None]:
    """
    Yield dicts for each supported file in the configured Drive folder.

    Each dict contains:
        - file_name (str): original file name
        - doc_id (str): Google Drive file ID
        - mime_type (str): MIME type of the file
        - content (bytes): raw file bytes
    """
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not folder_id:
        raise ValueError(
            "GDRIVE_FOLDER_ID environment variable is not set. "
            "Provide the Google Drive folder ID to sync from."
        )

    service = _build_service()
    files = _list_files(service, folder_id)
    logger.info("Found %d supported file(s) in Drive folder '%s'.", len(files), folder_id)

    for file in files:
        file_id = file["id"]
        file_name = file["name"]
        mime_type = file["mimeType"]

        logger.info("Downloading '%s' (id=%s, mime=%s).", file_name, file_id, mime_type)
        content = _download_file(service, file_id, mime_type)

        yield {
            "file_name": file_name,
            "doc_id": file_id,
            "mime_type": mime_type,
            "content": content,
        }
