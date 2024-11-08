import streamlit as st
import os
import json
from listen import parse_narrative_artifact
import gspread
from google.oauth2.service_account import Credentials
import datetime
import hashlib

from config import NARRATIVE_RESPONSES_FILE, SCOPES, SHEET_ID, LISTENING_TAGS_FILE, LISTENING_RESULTS_FILE, SEARCH_CARD_TEMPLATE_FILE, RESPONSE_STRATEGIES
from respond import generate_response

# Add these global declarations at the top level
sheet = None
responses_sheet = None

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


def load_listening_tags():
    if 'listening_tags' not in st.session_state:
        st.session_state.listening_tags = []
    return st.session_state.listening_tags

def save_listening_tags(tags_list):
    st.session_state.listening_tags = tags_list

def load_listening_responses():
    if 'listening_responses' not in st.session_state:
        st.session_state.listening_responses = []
    return st.session_state.listening_responses

def save_listening_responses(responses_list):
    st.session_state.listening_responses = responses_list


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

    # Initialize responses in session state if not exists
    if 'narrative_responses' not in st.session_state:
        st.session_state.narrative_responses = []
    
    # Check if entry with this ID exists
    existing_entry = next((item for item in st.session_state.narrative_responses 
                          if item["id"] == narrative["hash"]), None)
    if existing_entry:
        # Append new response to existing entry
        existing_entry["responses"].append(response_obj)
    else:
        # Add new entry
        st.session_state.narrative_responses.append(response_entry)


def handle_delete(narrative):
    """Handle deleting a narrative."""
    st.session_state.narrative_results = [
        n for n in st.session_state.narrative_results if n["hash"] != narrative["hash"]
    ]

def load_narrative_responses():
    """Load responses from session state."""
    if 'narrative_responses' not in st.session_state:
        st.session_state.narrative_responses = []
    return st.session_state.narrative_responses

def save_response_to_sheets(entry, response_idx):
    """Save a specific response to the Google Sheets responses worksheet."""
    if responses_sheet is None and not setup_google_sheets():
        st.error("Failed to setup Google Sheets connection")
        return
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

def setup_google_sheets():
    """Initialize connection to Google Sheets."""
    global sheet, responses_sheet
    try:
        credentials = get_google_credentials()
        gc = gspread.authorize(credentials)
        
        # Open the main spreadsheet and get the first worksheet
        spreadsheet = gc.open_by_key(SHEET_ID)
        sheet = spreadsheet.get_worksheet(0)  # First worksheet
        responses_sheet = spreadsheet.get_worksheet(1)  # Second worksheet
        
        return True
    except Exception as e:
        st.error(f"Failed to setup Google Sheets: {str(e)}")
        return False

def save_to_archive(narrative_data):
    """Save narrative data to Google Sheets archive."""
    try:
        # Use existing sheets connection
        if sheet is None and not setup_google_sheets():
            st.error("Failed to setup Google Sheets connection")
            return False
            
        # Prepare the row data
        row_data = [
            narrative_data.get("hash", ""),
            narrative_data.get("title", ""),
            narrative_data.get("narrative", ""),
            narrative_data.get("community", ""),
            narrative_data.get("link", ""),
            narrative_data.get("content", ""),    
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestam     
        ]
        
        # Append the row
        sheet.append_row(row_data)
        
        # Mark as archived in session state
        if 'archived_narratives' not in st.session_state:
            st.session_state.archived_narratives = set()
        st.session_state.archived_narratives.add(narrative_data.get("hash"))
        
        return True
    except Exception as e:
        st.error(f"Failed to save to archive: {str(e)}")
        return False

def is_archived(narrative_hash):
    """Check if a narrative has been archived."""
    if 'archived_narratives' not in st.session_state:
        st.session_state.archived_narratives = set()
    return narrative_hash in st.session_state.archived_narratives

###################
## STREAMLIT UI ##
###################

# Initialize Google Sheets connection - only do this once when the app starts
if 'sheets_initialized' not in st.session_state:
    st.session_state.sheets_initialized = setup_google_sheets()

if "listening_data" not in st.session_state:
    st.session_state.listening_data = load_listening_tags()

if "days_input" not in st.session_state:
    st.session_state.days_input = 7

st.title("COP29 Narrative Dashboard | Arkology Studio")
st.subheader("Rhizome 2024 /w Culture Hack Labs")


tab1, tab2, tab3, tab4, tab5 = st.tabs(["Listen", "Search", "Respond", "Archive", "Config"])

# Listening
with tab1:
    st.header("Listening Model")
    
    # Create a form
    with st.form(key="settings_form"):

        if 'num_results' not in st.session_state:
            st.session_state['num_results'] = 5
        if 'days_input' not in st.session_state:
            st.session_state['days_input'] = 7
        
        # All form inputs go here
        temp_num_results = st.slider(
            "Number of results:", 
            min_value=1, 
            max_value=10, 
            value=st.session_state.get('num_results', 5),
            step=1
        )

        listening_data_str = "\n".join(load_listening_tags())
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
        with st.spinner('Searching narratives...'):
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
                    if not is_archived(narrative["hash"]):
                        if st.button("Save to archive", key=f"archive_{narrative['hash']}"):
                            if save_to_archive(narrative):
                                st.success("Saved to archive!")
                                st.rerun()
                    else:
                        st.write("✓ Archived")
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
            st.session_state.narrative_responses = []
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

# Add new Config tab at the end
with tab5:
    st.header("Configuration")
    
    # Exa Configuration
    exa_api_key = st.text_input(
        "Exa API Key",
        value=st.session_state.get("exa_api_key", ""),
        type="password",
        help="If provided, this will override the API key in secrets.toml"
    )
    if exa_api_key:
        st.session_state["exa_api_key"] = exa_api_key
        os.environ["EXA_API_KEY"] = exa_api_key

