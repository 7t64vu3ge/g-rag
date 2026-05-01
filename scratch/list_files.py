import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def list_all_accessible_files():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not creds_path or not os.path.exists(creds_path):
        print("ERROR: Credentials file not found!")
        return

    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=credentials)
    
    try:
        results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name, mimeType)").execute()
        items = results.get('files', [])

        if not items:
            print('No files found.')
        else:
            print('Files accessible to service account:')
            for item in items:
                print(f"{item['name']} ({item['id']})")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    list_all_accessible_files()
