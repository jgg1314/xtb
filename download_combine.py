import os
import pickle
import io
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
import google_auth_oauthlib.flow
import googleapiclient.errors
import dotenv
from xtb_functions import authenticate, fetch_and_combine_csvs_from_folder

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly']
CREDENTIALS_FILE = 'credentials.json'

folder_name = 'xtb'
save_path="combined_xtb.xlsx"

service = authenticate()

combined_df = fetch_and_combine_csvs_from_folder(service, folder_name, save_path=save_path)