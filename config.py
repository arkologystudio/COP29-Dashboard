import os
import json
import streamlit as st
from dotenv import load_dotenv

# Load .env file if it exists (local development)
load_dotenv()

def get_google_credentials():
    """Get Google credentials from environment or session state"""
    if "google_service_account" in st.session_state:
        return st.session_state["google_service_account"]
    
    # Try to get from environment
    json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Fallback to file if it exists
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        with open(SERVICE_ACCOUNT_FILE, 'r') as f:
            return json.load(f)
    
    return None

# API Keys with fallbacks
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.session_state.get("openai_api_key")
EXA_API_KEY = os.getenv("EXA_API_KEY") or st.session_state.get("exa_api_key")

# Assistant IDs (these could also be moved to .env if they change frequently)
NARRATIVE_IDENTIFICATION_ASSISTANT = "asst_nn5V0Kytzv90U3qcdmfVcFBg"

# File paths
LISTENING_TAGS_FILE = "data/listening_tags.json"
LISTENING_RESULTS_FILE = "data/listening_responses.json"
NARRATIVE_RESPONSES_FILE = "data/narrative_responses.json"
SEARCH_CARD_TEMPLATE_FILE = "templates/search_result_card.html"

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'cop29-resources-archive-sheet-b1f6dc1221fa.json'
SHEET_ID = os.getenv("GOOGLE_SHEET_ID") or st.session_state.get("sheet_id", "1y3rOqpZ1chq7SNdxRIdeHyhi7Kp0YL5UGbbUKDkjA-M")

# Response strategies
RESPONSE_STRATEGIES = {
    "Truth Query": "asst_MDjAUuSTMgphokc3v5BZLKCT",
    "Perspective Broadening": "asst_MDjAUuSTMgphokc3v5BZLKCT",
    "Combined": "asst_MDjAUuSTMgphokc3v5BZLKCT"
}