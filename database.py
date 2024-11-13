import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from functools import lru_cache

@lru_cache(maxsize=1)
def get_sheets():
    """Get or create worksheet connections."""
    try:
        credentials = get_google_credentials()
        gc = gspread.authorize(credentials)
        
        SHEET_ID = st.secrets["google"]["sheet_id"]
        spreadsheet = gc.open_by_key(SHEET_ID)
        
        return {
            'narrative': spreadsheet.worksheet('Narrative Results'),
            'responses': spreadsheet.worksheet('Responses'),
            'threads': spreadsheet.worksheet('Threads')
        }
    except Exception as e:
        st.error(f"Failed to setup Google Sheets: {str(e)}")
        return None

def setup_google_sheets():
    """Initialize connection to Google Sheets."""
    return get_sheets() is not None

# Setup Google Sheets
def get_google_credentials():
    """Create service account credentials from secrets."""

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    service_account_info = st.secrets["google"]

    credentials_dict = {
        "type": "service_account",
        "project_id": service_account_info["project_id"],
        "private_key_id": service_account_info["private_key_id"],
        "private_key": service_account_info["private_key"],
        "client_email": service_account_info["client_email"],
        "client_id": service_account_info["client_id"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": service_account_info["client_x509_cert_url"]
    }
    return Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
