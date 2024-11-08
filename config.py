import streamlit as st

# Assistant IDs for OpenAI
NARRATIVE_IDENTIFICATION_ASSISTANT = "asst_nn5V0Kytzv90U3qcdmfVcFBg"

# File paths
LISTENING_TAGS_FILE = "data/listening_tags.json"
LISTENING_RESULTS_FILE = "data/listening_responses.json"
NARRATIVE_RESPONSES_FILE = "data/narrative_responses.json"

SEARCH_CARD_TEMPLATE_FILE = "templates/search_result_card.html"

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'service_account_info.json'  # This will be created dynamically
SHEET_ID = st.secrets["google_sheets"]["sheet_id"]

# Assistant ID mappings for different response strategies
RESPONSE_STRATEGIES = {
    "Truth Query": st.secrets["openai"]["truth_query_assistant_id"],
    "Perspective Broadening": st.secrets["openai"]["perspective_assistant_id"],
    "Combined": st.secrets["openai"]["combined_assistant_id"]
}