import streamlit as st
import os
import json
from listening import get_responding_data
import gspread
from google.oauth2.service_account import Credentials
import datetime
import hashlib

# File paths
LISTENING_TAGS_FILE = "listening_tags.json"
LISTENING_RESPONSES_FILE = "listening_responses.json"
CARD_TEMPLATE_FILE = "templates/response_card.html"

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'cop29-resources-archive-sheet-b1f6dc1221fa.json'
SHEET_ID = '1y3rOqpZ1chq7SNdxRIdeHyhi7Kp0YL5UGbbUKDkjA-M'

credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)
sheet = client.open_by_key(SHEET_ID).sheet1

def load_listening_tags():
    if os.path.exists(LISTENING_TAGS_FILE):
        try:
            with open(LISTENING_TAGS_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            st.error(f"Error: {LISTENING_TAGS_FILE} contains invalid JSON. Resetting to an empty list.")
            return []
    return []

def save_listening_tags(tags_list):
    with open(LISTENING_TAGS_FILE, "w", encoding="utf-8") as file:
        json.dump(tags_list, file, indent=4)

def load_listening_responses():
    if os.path.exists(LISTENING_RESPONSES_FILE):
        try:
            with open(LISTENING_RESPONSES_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            st.error(f"Error: {LISTENING_RESPONSES_FILE} contains invalid JSON. Resetting to an empty list.")
            return []
    return []

def save_listening_responses(responses_list):
    with open(LISTENING_RESPONSES_FILE, "w", encoding="utf-8") as file:
        json.dump(responses_list, file, indent=4)

def append_to_google_sheets(narrative):
    row_data = [
        narrative['title'],
        narrative['narrative'],
        narrative['community'],
        narrative['link'],
        narrative['content'],
        datetime.date.today().strftime("%Y-%m-%d")
    ]
    sheet.append_row(row_data)

def delete_response(title):
    """Delete a narrative from session state based on title."""
    st.session_state.responding_data = [
        narrative for narrative in st.session_state.responding_data if narrative["title"] != title
    ]
    st.success("Deleted successfully")

def load_card_template():
    with open(CARD_TEMPLATE_FILE, "r", encoding="utf-8") as file:
        return file.read()

def generate_unique_key(narrative, unique_suffix):
    """Generate a truly unique key using a hash and a unique suffix."""
    base_key = f"{narrative['title']}_{narrative['link']}_{narrative['content']}"
    return hashlib.md5((base_key + unique_suffix).encode()).hexdigest()

###################

if "listening_data" not in st.session_state:
    st.session_state.listening_data = load_listening_tags()

if "days_input" not in st.session_state:
    st.session_state.days_input = 2

st.title("Dashboard")

tab1, tab2, tab3 = st.tabs(["Listen", "Narrative Artifacts", "Archive"])

# Listening
with tab1:
    st.header("Listening Model")

    listening_data_str = "\n".join(st.session_state.listening_data)
    user_input = st.text_area("Enter list of search terms (one phrase per line):", listening_data_str, placeholder="e.g.\nCarbon storage and capture devices\nCarbon credit markets\nInvestment in clean energy", height=160)
    
    if st.button("Update List"):
        st.session_state.listening_data = user_input.split("\n")
        save_listening_tags(st.session_state.listening_data)
        st.success("List updated successfully!")

    days_input = st.number_input("Enter number of days in the past to search:", min_value=0, max_value=365, value=7, step=1)
    
    st.session_state.days_input = days_input
    st.write(f"Stored days_input in session state: {st.session_state.days_input}")

# Results
with tab2:
    st.header("Search")
    st.write("Search & process narrative artifacts")

    if st.button("Find Narratives"):
        # Initialize or reset the responding data list in session state
        if "responding_data" not in st.session_state:
            st.session_state.responding_data = []
        
        # Placeholder to progressively display parsed narratives
        response_placeholder = st.empty()
        
        for narrative in get_responding_data(st.session_state.days_input):
            # Check if the narrative is already in responding_data by its unique content hash
            narrative_hash = hashlib.md5(f"{narrative['title']}_{narrative['link']}_{narrative['content']}".encode()).hexdigest()
            if any(item.get("hash") == narrative_hash for item in st.session_state.responding_data):
                continue  # Skip if the narrative is already processed
            
            # Add hash to narrative and append to session state
            narrative["hash"] = narrative_hash
            st.session_state.responding_data.append(narrative)

            # Render each unique narrative card as it becomes available
            with response_placeholder.container():
                card_template = load_card_template()
                for narrative_idx, narrative in enumerate(st.session_state.responding_data):
                    card_html = card_template.replace("{{ title }}", narrative['title']) \
                                             .replace("{{ narrative }}", narrative['narrative']) \
                                             .replace("{{ community }}", narrative.get('community', 'N/A')) \
                                             .replace("{{ link }}", narrative['link']) \
                                             .replace("{{ content }}", narrative['content'])
                    st.markdown(card_html, unsafe_allow_html=True)

                    # Generate unique keys for each button using a timestamp to prevent re-use
                    unique_suffix = f"{narrative_idx}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
                    archive_key = generate_unique_key(narrative, unique_suffix + "_archive")
                    delete_key = generate_unique_key(narrative, unique_suffix + "_delete")

                    # Display action buttons with truly unique keys
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Archive", key=archive_key, on_click=append_to_google_sheets, args=(narrative,)):
                            st.success("Archived successfully")
                    with col2:
                        if st.button("Delete", key=delete_key, on_click=delete_response, args=(narrative['title'],)):
                            st.success("Deleted successfully")
    else:
        st.write("No narrative artifacts yet. Please refer to the Listen tab to set search criteria first, then use the 'Find Narratives' button to retrieve narrative artifacts.")


# Archive:
with tab3: 
    st.header("Archive")
    st.write("View the archived responses in the Google Sheet:")
    st.markdown(f"[See archived responses](https://docs.google.com/spreadsheets/d/1y3rOqpZ1chq7SNdxRIdeHyhi7Kp0YL5UGbbUKDkjA-M/edit?usp=sharing)", unsafe_allow_html=True)


