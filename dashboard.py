import streamlit as st
import os
import json
from listen import parse_narrative_artifact
import gspread
from google.oauth2.service_account import Credentials
import datetime
import hashlib

from config import NARRATIVE_RESPONSES_FILE, SERVICE_ACCOUNT_FILE, SCOPES, SHEET_ID, LISTENING_TAGS_FILE, LISTENING_RESULTS_FILE, SEARCH_CARD_TEMPLATE_FILE, RESPONSE_STRATEGIES
from respond import generate_response

# Setup Google Sheets
def get_google_credentials():
    """Create service account credentials from secrets."""
    service_account_info = st.secrets["google_sheets"]
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

credentials = get_google_credentials()
client = gspread.authorize(credentials) 
sheet = client.open_by_key(SHEET_ID).sheet1
responses_sheet = client.open_by_key(SHEET_ID).worksheet("Responses")  # Add new sheet for responses

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
    if os.path.exists(LISTENING_RESULTS_FILE):
        try:
            with open(LISTENING_RESULTS_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            st.error(f"Error: {LISTENING_RESULTS_FILE} contains invalid JSON. Resetting to an empty list.")
            return []
    return []

def save_listening_responses(responses_list):
    with open(LISTENING_RESULTS_FILE, "w", encoding="utf-8") as file:
        json.dump(responses_list, file, indent=4)

def append_to_google_sheets(narrative):
    row_data = [
        narrative['hash'],
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
    st.session_state.narrative_results = [
        narrative for narrative in st.session_state.narrative_results if narrative["title"] != title
    ]
    st.success("Deleted successfully")

def load_card_template(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def generate_unique_key(narrative, unique_suffix):
    """Generate a truly unique key using a hash and a unique suffix."""
    base_key = f"{narrative['title']}_{narrative['link']}_{narrative['content']}"
    return hashlib.md5((base_key + unique_suffix).encode()).hexdigest()

def handle_generate_response(narrative, strategy):
    """Handle response generation for a narrative with specific strategy."""
    assistant_id = RESPONSE_STRATEGIES[strategy]
    res = generate_response(narrative, assistant_id)
    print("LLM RESPONSE: ", res)
    
    # Create response object with strategy metadata
    response_obj = {
        "content": res,
        "strategy": strategy,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Create response entry with all narrative data
    response_entry = {
        "id": narrative["hash"],
        "original_post": {
            "title": narrative["title"],
            "narrative": narrative["narrative"],
            "community": narrative.get("community", "N/A"),
            "link": narrative["link"],
            "content": narrative["content"],
            "date": datetime.date.today().strftime("%Y-%m-%d")
        },
        "responses": [response_obj] if res else []
    }

    try:
        with open(NARRATIVE_RESPONSES_FILE, "r") as f:
            responses = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        responses = []
    
    # Check if entry with this ID exists
    existing_entry = next((item for item in responses if item["id"] == narrative["hash"]), None)
    if existing_entry:
        # Append new response to existing entry
        existing_entry["responses"].append(response_obj)
    else:
        # Add new entry
        responses.append(response_entry)
    
    # Save updated responses
    with open(NARRATIVE_RESPONSES_FILE, "w") as f:
        json.dump(responses, f, indent=4)

def handle_archive(narrative):
    """Handle archiving a narrative."""
    append_to_google_sheets(narrative)
    # Remove from narrative_results after archiving
    st.session_state.narrative_results = [
        n for n in st.session_state.narrative_results if n["hash"] != narrative["hash"]
    ]

def handle_delete(narrative):
    """Handle deleting a narrative."""
    st.session_state.narrative_results = [
        n for n in st.session_state.narrative_results if n["hash"] != narrative["hash"]
    ]

def load_narrative_responses():
    """Load responses from the narrative responses file."""
    try:
        with open(NARRATIVE_RESPONSES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_response_to_sheets(entry, response_idx):
    """Save a specific response to the Google Sheets responses worksheet."""
    id = entry["id"]
    original_post = entry["original_post"]
    response = entry["responses"][response_idx]

    row_data = [
        id,
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
        original_post["title"],
        original_post["content"],
        original_post["link"],
        response["content"],
        response["strategy"],
    ]
    responses_sheet.append_row(row_data)

###################
## STREAMLIT UI ##
###################

if "listening_data" not in st.session_state:
    st.session_state.listening_data = load_listening_tags()

if "days_input" not in st.session_state:
    st.session_state.days_input = 7

st.title("COP29 Narrative Dashboard | Arkology Studio")
st.subheader("Rhizome 2024 /w Culture Hack Labs")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Listen", "Search", "Respond", "Archive"])

# Listening
with tab1:
    st.header("Listening Model")
    
    # Create a form
    with st.form(key="settings_form"):
        # All form inputs go here
        temp_num_results = st.slider(
            "Number of results:", 
            min_value=1, 
            max_value=10, 
            value=st.session_state.get('num_results', 5),
            step=1
        )

        listening_data_str = "\n".join(st.session_state.listening_data)
        temp_user_input = st.text_area(
            "Enter list of search terms (one phrase per line):", 
            listening_data_str, 
            placeholder="e.g.\nCarbon storage and capture devices\nCarbon credit markets\nInvestment in clean energy", 
            height=160
        )
        
        temp_days_input = st.number_input(
            "Enter number of days in the past to search:", 
            min_value=0, 
            max_value=365, 
            value=st.session_state.get('days_input', 7), 
            step=1
        )
        
        # Form submit button
        submit_button = st.form_submit_button("Confirm Settings")
        
        if submit_button:
            st.session_state.num_results = temp_num_results
            st.session_state.listening_data = temp_user_input.split("\n")
            st.session_state.days_input = temp_days_input
            
            # Save to file
            save_listening_tags(st.session_state.listening_data)
            
            st.success("All settings updated successfully!")
    
    # Display current settings outside the form
    with st.expander("Current Settings"):
        st.write(f"Number of results: {st.session_state.get('num_results', 5)}")
        st.write(f"Days to search: {st.session_state.get('days_input', 7)}")
        st.write("Search terms:")
        for term in st.session_state.listening_data:
            st.write(f"- {term}")

# Results
with tab2:
    st.header("Search & Review")
    st.write("Search & review retrieved narrative artifacts")

    if st.button("Find Narratives"):
        st.session_state.narrative_results = []
        
        progress_container = st.empty()
        with st.spinner('Fetching narratives...'):
            for narrative in parse_narrative_artifact(st.session_state.days_input):
                narrative_hash = hashlib.md5(f"{narrative['title']}_{narrative['link']}_{narrative['content']}".encode()).hexdigest()
                if any(item.get("hash") == narrative_hash for item in st.session_state.narrative_results):
                    continue
                
                narrative["hash"] = narrative_hash
                st.session_state.narrative_results.append(narrative)
                
                # Update progress message
                progress_container.text(f"Processed {len(st.session_state.narrative_results)} artifacts ...")
            
            # Clear the progress message when done
            progress_container.empty()
            
            if not st.session_state.narrative_results:
                st.write("No new narratives found.")
            st.rerun()  # Rerun to display the updated narratives in the main display section
    
    # Single display section for narratives
    if "narrative_results" in st.session_state and st.session_state.narrative_results:
        card_template = load_card_template(SEARCH_CARD_TEMPLATE_FILE)
        for narrative_idx, narrative in enumerate(st.session_state.narrative_results):
            card_html = card_template.replace("{{ title }}", narrative['title']) \
                                    .replace("{{ narrative }}", narrative['narrative']) \
                                    .replace("{{ community }}", narrative.get('community', 'N/A')) \
                                    .replace("{{ link }}", narrative['link']) \
                                    .replace("{{ content }}", narrative['content']) \
                                    .replace("{{ favorite_count }}", narrative.get('favorite_count', 'N/A')) \
                                    .replace("{{ reply_count }}", narrative.get('reply_count', 'N/A')) \
                                    .replace("{{ quote_count }}", narrative.get('quote_count', 'N/A')) \
                                    .replace("{{ retweet_count }}", narrative.get('retweet_count', 'N/A'))
            st.markdown(card_html, unsafe_allow_html=True)

            unique_suffix = f"{narrative_idx}_{narrative['hash']}"
            
            # Create two columns with different widths (7:3 ratio)
            left_col, right_col = st.columns([0.7, 0.3])
            
            with left_col:
                # Create sub-columns for response controls with more balanced widths
                with st.form(key=f"response_form_{unique_suffix}"):
                    resp_col1, resp_col2 = st.columns([0.3, 0.7])
                    with resp_col2:
                        strategy = st.selectbox(
                            "Response Strategy",
                            options=list(RESPONSE_STRATEGIES.keys()),
                            key=f"strategy_{unique_suffix}",
                            label_visibility="collapsed"
                        )
                    with resp_col1:
                        submit_response = st.form_submit_button("Respond")
                        if submit_response:
                            handle_generate_response(narrative, strategy)
                            st.success("Response generated successfully!")
            
            with right_col:
                # Create sub-columns for Archive/Delete
                act_col1, act_col2 = st.columns([0.5, 0.5])
                with act_col1:
                    if st.button("Archive", key=f"archive_{unique_suffix}", type="secondary"):
                        handle_archive(narrative)
                        st.rerun()
                with act_col2:
                    if st.button("Remove", key=f"delete_{unique_suffix}", type="secondary"):
                        handle_delete(narrative)
                        st.rerun()
    else:
        st.write("No narrative artifacts yet. Please refer to the Listen tab to set search criteria first, then use the 'Find Narratives' button to retrieve narrative artifacts.")

with tab3:
    st.header("Respond")
    
    responses_data = load_narrative_responses()
    if not responses_data:
        st.write("No responses generated yet. Generate responses in the Search tab first.")
    else:
        # Add Clear All button
        if st.button("Clear All Responses", type="primary"):
            # Clear the responses file
            with open(NARRATIVE_RESPONSES_FILE, "w") as f:
                json.dump([], f)
            st.success("All responses cleared!")
            st.rerun()
            
        for entry in responses_data:
            with st.expander(f"🔍 {entry['original_post']['title']}", expanded=False):
                # Display original post details
                st.markdown(f"**Original Content:** {entry['original_post']['content']}")
                st.markdown(f"**Source:** [{entry['original_post']['link']}]({entry['original_post']['link']})")
                
                # Display responses
                st.markdown("### Generated Responses")
                for idx, response in enumerate(entry['responses']):
                    with st.container():
                        st.markdown("---")
                        st.markdown(f"**Response {idx + 1}** (Strategy: {response['strategy']})")
                        st.markdown(response['content'])
                        if st.button("Save to Archive", key=f"save_{entry['id']}_{idx}"):
                            save_response_to_sheets(entry, idx)
                            st.success("Response saved to archive!")

# Archive:
with tab4: 
    st.header("Archive")
    st.write("View the archived responses in the Google Sheet:")
    st.markdown(f"[See archived responses](https://docs.google.com/spreadsheets/d/1y3rOqpZ1chq7SNdxRIdeHyhi7Kp0YL5UGbbUKDkjA-M/edit?usp=sharing)", unsafe_allow_html=True)

