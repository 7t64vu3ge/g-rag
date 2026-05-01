import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def test_gdrive():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    
    print(f"Using credentials from: {creds_path}")
    print(f"Target Folder ID: {folder_id}")
    
    if not creds_path or not os.path.exists(creds_path):
        print("ERROR: Credentials file not found!")
        return

    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=credentials)
    
    try:
        # Check folder access
        folder = service.files().get(fileId=folder_id, fields="name").execute()
        print(f"Connected successfully! Folder name: {folder.get('name')}")
        
        # List files
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        files = results.get('files', [])
        
        if not files:
            print("No files found in the folder.")
        else:
            print(f"Found {len(files)} files:")
            for file in files:
                print(f"- {file['name']} (ID: {file['id']}, MIME: {file['mimeType']})")
                
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_gdrive()
