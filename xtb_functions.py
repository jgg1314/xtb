import json
import websocket
import pandas as pd
from datetime import datetime
import os
import io
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import google.auth
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
import pickle
import dotenv
import sys

def get_trades(user_id, password):
    try:
        ws = websocket.create_connection("wss://ws.xtb.com/demo")

        login_payload = {
            "command": "login",
            "arguments": {"userId": user_id, "password": password}
        }
        ws.send(json.dumps(login_payload))
        response = json.loads(ws.recv())

        if response.get('status'):
            print("Login successful.")
        else:
            print(f"Login failed, termination of run.")
            sys.exit()

        trades_payload = {"command": "getTrades", "arguments": {"openedOnly": False}}
        ws.send(json.dumps(trades_payload))
        trades_response = json.loads(ws.recv())

        ws.send(json.dumps({"command": "logout"}))
        ws.close()
        print("Logged out and connection closed.")

        return trades_response["returnData"]

    except Exception as e:
        print(f"An error occurred: {e}")


def process_df(df):
    load_timestamp = datetime.now()
    load_date = load_timestamp.strftime("%Y_%m_%d")
    
    csv_name = f"{load_date}_xtb.csv"
    csv_path = fr"C:\Users\PC\Desktop\all_stuff\xtb\csv_save\{csv_name}"
    
    df["load_timestamp"] = load_timestamp
    df.to_csv(csv_path, index=False)
    
    return df, csv_path

# Authenticate and create the service
def authenticate():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    service = googleapiclient.discovery.build('drive', 'v3', credentials=creds)
    return service

# Get folder ID by name
def get_folder_id_by_name(service, folder_name):
    # Query to search for the folder by name
    query = f"mimeType='application/vnd.google-apps.folder' and name = '{folder_name}'"
    
    try:
        # List files and folders matching the query
        results = service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get('files', [])
        
        # If folder is found, return its ID
        if folders:
            return folders[0]['id']
        else:
            print(f"No folder named '{folder_name}' found.")
            return None
    except Exception as error:
        print(f"An error occurred: {error}")
        return None

# Check if the file already exists in the folder
def file_exists(service, file_name, folder_id):
    query = f"'{folder_id}' in parents and name = '{file_name}'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    return files[0] if files else None

# Upload CSV file to Google Drive
def upload_csv(file_path, folder_name):
    service = authenticate()

    # Get folder ID by folder name
    folder_id = get_folder_id_by_name(service, folder_name)
    if not folder_id:
        print(f"Folder '{folder_name}' not found.")
        return

    # Prepare file metadata
    file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
    
    media = googleapiclient.http.MediaFileUpload(file_path, mimetype='text/csv')

    # Check if file already exists in the folder
    existing_file = file_exists(service, file_metadata['name'], folder_id)
    
    if existing_file:
        # If file exists, delete it
        print(f"File {file_metadata['name']} already exists. Deleting it.")
        service.files().delete(fileId=existing_file['id']).execute()

    # Upload the file
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name'
        ).execute()

        print(f'File {file["name"]} uploaded successfully! (ID: {file["id"]})')
    except googleapiclient.errors.HttpError as error:
        print(f'An error occurred: {error}')


def fetch_and_combine_csvs_from_folder(service, folder_name, save_path):
    """Fetch all CSV files from a Google Drive folder and combine them into a single DataFrame."""
    # Get the folder ID from the folder name
    folder_id = get_folder_id_by_name(service, folder_name)
    if not folder_id:
        return None
    
    # Query to find all CSV files in the folder and exclude trashed files
    query = f"'{folder_id}' in parents and mimeType='text/csv' and trashed = false"
    
    # List to hold DataFrames
    dataframes = []
    
    try:
        # Fetch the list of CSV files in the folder (pagination is handled)
        page_token = None
        while True:
            results = service.files().list(
                q=query,
                fields="nextPageToken, files(id, name)",
                pageToken=page_token
            ).execute()
            
            # Get files from the response
            files = results.get('files', [])
            
            # If there are no CSV files, print a message
            if not files:
                print(f"No CSV files found in folder '{folder_name}'.")
            else:
                for file in files:
                    print(f"Downloading CSV file: {file['name']}...")
                    
                    # Fetch the file content
                    request = service.files().get_media(fileId=file['id'])
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while done is False:
                        _, done = downloader.next_chunk()
                    
                    # Read the CSV file into a pandas DataFrame
                    fh.seek(0)
                    df = pd.read_csv(fh)
                    dataframes.append(df)
            
            # Check if there are more pages of results
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        # Combine all DataFrames into one
        if dataframes:
            combined_df = pd.concat(dataframes, ignore_index=True)
            print(f"Combined DataFrame with {len(combined_df)} rows.")
            combined_df.to_excel(save_path, index=False)
            return combined_df
        else:
            print(f"No CSV files found in folder '{folder_name}'.")
            return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
