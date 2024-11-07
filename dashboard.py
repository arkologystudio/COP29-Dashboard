import streamlit as st
import os
import json
from listening import get_responding_data
import gspread
from google.oauth2.service_account import Credentials
import datetime

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

def remove_response(title):
    responses = load_listening_responses()
    updated_responses = [r for r in responses if r["title"] != title]
    
    for narrative in responses:
        if narrative["title"] == title:
            append_to_google_sheets(narrative)
            break

    save_listening_responses(updated_responses)
    return updated_responses

def delete_response(title):
    responses = load_listening_responses()
    updated_responses = [r for r in responses if r["title"] != title]
    save_listening_responses(updated_responses)
    return updated_responses

def load_card_template():
    with open(CARD_TEMPLATE_FILE, "r", encoding="utf-8") as file:
        return file.read()

if "listening_data" not in st.session_state:
    st.session_state.listening_data = load_listening_tags()

if "responding_data" not in st.session_state:
    st.session_state.responding_data = load_listening_responses()
    
if "days_input" not in st.session_state:
    st.session_state.days_input = 2

st.title("Dashboard")

tab1, tab2, tab3 = st.tabs(["Listen", "Narrative Artifacts", "Archive"])

# Listening
with tab1:
    st.header("Listen")

    listening_data_str = "\n".join(st.session_state.listening_data)
    user_input = st.text_area("Enter list of search terms (one phrase per line):", listening_data_str, placeholder="e.g.\nCarbon storage and capture devices\nCarbon credit markets\nInvestment in clean energy",  height=160)
    
    if st.button("Update List"):
        st.session_state.listening_data = user_input.split("\n")
        save_listening_tags(st.session_state.listening_data)
        st.success("List updated successfully!")

    days_input = st.number_input("Enter number of days in the past to search:", min_value=0, max_value=365, value=7, step=1)
    
    st.session_state.days_input = days_input
    st.write(f"Stored days_input in session state: {st.session_state.days_input}")

# Results
with tab2:
    st.header("Narrative Artifacts")
    st.write("List of narrative artifacts retrieved via neural search")

    if st.button("Find Narratives"):
        responding_data = get_responding_data(st.session_state.days_input)
        st.session_state.responding_data = responding_data
        st.success("Narrative artifacts fetched successfully")

    st.write("---")

        
    if st.session_state.responding_data:
        card_template = load_card_template()
        count = 0
        for narrative in st.session_state.responding_data:
            card_html = card_template.replace("{{ title }}", narrative['title']) \
                                    .replace("{{ narrative }}", narrative['narrative']) \
                                    .replace("{{ community }}", narrative.get('community', 'N/A')) \
                                    .replace("{{ link }}", narrative['link']) \
                                    .replace("{{ content }}", narrative['content'])

            st.markdown(card_html, unsafe_allow_html=True)

            col1, col2, col3, col4, col5, col6, col7 = st.columns([0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3])

            with col1:
                if st.button("Archive", key=f"archive_{narrative['title']}_{count}", on_click=remove_response, args=(narrative['title'],)):
                    st.session_state.dummy_flag = not st.session_state.get('dummy_flag', False)
                
            with col2:
                if st.button("Delete", key=f"delete_{narrative['title']}_{count}", on_click=delete_response, args=(narrative['title'],)):
                    st.session_state.dummy_flag = not st.session_state.get('dummy_flag', False)
                
            count += 1
    else:
        st.write("No narrative artifacts yet. Please refer to the Listen tab to set search criteria first, then use the 'Find Narratives' button to retrieve narrative artifacts.")

# Archive:
with tab3: 
    st.header("Saved Responses")
    st.write("View the archived responses in the Google Sheet:")
    st.markdown(f"[See archived responses](https://docs.google.com/spreadsheets/d/1y3rOqpZ1chq7SNdxRIdeHyhi7Kp0YL5UGbbUKDkjA-M/edit?usp=sharing)", unsafe_allow_html=True)
