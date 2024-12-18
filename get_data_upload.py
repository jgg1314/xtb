import json
import websocket
import pandas as pd
from datetime import datetime
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import google.auth
from google.auth.transport.requests import Request
import pickle
import dotenv
import sys
from xtb_functions import get_trades, process_df, authenticate, get_folder_id_by_name, file_exists, upload_csv

dotenv.load_dotenv()
user_id = os.getenv("USER_ID")
password = os.getenv("PASSWORD")

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly']
CREDENTIALS_FILE = 'credentials.json'

xtb_data = get_trades(user_id, password)
df = pd.DataFrame(xtb_data)

df_processed, csv_file_path = process_df(df)
folder_name = 'xtb'

upload_csv(csv_file_path, folder_name)

sys.exit()