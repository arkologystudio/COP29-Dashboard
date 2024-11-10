import gspread
import streamlit as st
import os
from database import get_google_credentials, setup_google_sheets, get_sheets
from listen import parse_narrative_artifact, search_narrative_artifacts
import datetime
import hashlib

from config import SEARCH_CARD_TEMPLATE_FILE, RESPONSE_STRATEGIES
from respond import generate_response

narrative_sheet = None
responses_sheet = None

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

def handle_generate_response(narrative, strategy):
    """Handle response generation for a narrative with specific strategy."""
    assistant_id = RESPONSE_STRATEGIES[strategy]
    res = generate_response(narrative, assistant_id)
    
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

def save_response_to_sheets(response_data, idx):
    """Save response data to Google Sheets archive."""
    try:
        # Get fresh connection to sheets
        sheets = get_sheets()
        if not sheets:
            st.error("Could not access worksheets")
            return False
            
        responses_sheet = sheets['responses']
        
        # Prepare the row data
        row_data = [
            response_data["id"],
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            response_data["original_post"]["title"],
            response_data["original_post"]["content"],
            response_data["original_post"]["link"],
            response_data["responses"][idx]["content"],
            response_data["responses"][idx]["strategy"],
            "FALSE"
        ]

        responses_sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Failed to save to archive: {str(e)}")
        return False

def save_narrative_artifact_to_sheets(narrative_data):
    """Save narrative data to Google Sheets archive."""
    try:
        # Get fresh connection to sheets
        sheets = get_sheets()
        if not sheets:
            st.error("Could not access worksheets")
            return False
            
        narrative_sheet = sheets['narrative']
        
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
        narrative_sheet.append_row(row_data)
        
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

st.title("Narrative Dashboard")
st.subheader("Rhizome 2024 | Arkology Studio & Culture Hack Labs")


tab1, tab2, tab3, tab4, tab5 = st.tabs(["Listen", "Search", "Responses", "Archive", "Config"])

# Listening
with tab1:
    st.header("Listening Model")
    
    # Create a form
    with st.form(key="settings_form"):

        if 'num_results' not in st.session_state:
            st.session_state['num_results'] = 5
        if 'days_input' not in st.session_state:
            st.session_state['days_input'] = 7
        if 'search_type' not in st.session_state:
            st.session_state['search_type'] = 'neural'
        if 'use_autoprompt' not in st.session_state:
            st.session_state['use_autoprompt'] = True
        if 'livecrawl' not in st.session_state:
            st.session_state['livecrawl'] = None
        
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
            height=160,
        )
        
        temp_days_input = st.number_input(
            "Enter number of days in the past to search:", 
            min_value=0, 
            max_value=365, 
            value=st.session_state.get('days_input', 7), 
            step=1
        )

        temp_search_type = st.selectbox(
            "Search type:",
            options=["neural", "keyword", "auto"],
            index=["neural", "keyword", "auto"].index(st.session_state.get('search_type', 'neural'))
        )

        temp_use_autoprompt = st.checkbox(
            "Use autoprompt",
            value=st.session_state.get('use_autoprompt', True)
        )

        temp_livecrawl = st.selectbox(
            "Live crawl:",
            options=[None, "always"],
            index=[None, "always"].index(st.session_state.get('livecrawl', None))
        )
        
        # Form submit button
        submit_button = st.form_submit_button("Confirm Settings")
        
        if submit_button:
            st.session_state.num_results = temp_num_results
            st.session_state.listening_data = temp_user_input.split("\n")
            st.session_state.days_input = temp_days_input
            st.session_state.search_type = temp_search_type
            st.session_state.use_autoprompt = temp_use_autoprompt
            st.session_state.livecrawl = temp_livecrawl
            
            # Save to file
            save_listening_tags(st.session_state.listening_data)
            
            st.success("All settings updated successfully!")
    
    # Display current settings outside the form
    with st.expander("Current Settings"):
        st.write(f"Number of results: {st.session_state.get('num_results', 5)}")
        st.write(f"Days to search: {st.session_state.get('days_input', 7)}")
        st.write(f"Search type: {st.session_state.get('search_type', 'neural')}")
        st.write(f"Use autoprompt: {st.session_state.get('use_autoprompt', True)}")
        st.write(f"Live crawl: {st.session_state.get('livecrawl', None)}")
        st.write("Search terms:")
        for term in st.session_state.listening_data:
            st.write(f"- {term}")

# Results
with tab2:
    st.header("Search & Review")
    st.write("Search & review retrieved narrative artifacts")

    if st.button("Find Narratives"):
        # Initialize results list if it doesn't exist
        if "narrative_results" not in st.session_state:
            st.session_state.narrative_results = []
        
        progress_container = st.empty()
        with st.spinner('Searching narratives...'):
            # First search for artifacts
            search_results = search_narrative_artifacts(days=st.session_state.days_input)
            
            # Track new narratives found in this search
            new_narratives_found = False
            
            # Then parse each artifact
            for narrative in parse_narrative_artifact(search_results):
                # Check if this narrative is already in results
                if not any(item.get("hash") == narrative["hash"] for item in st.session_state.narrative_results):
                    st.session_state.narrative_results.append(narrative)
                    new_narratives_found = True
                
                # Update progress message
                progress_container.text(f"Processed {len(st.session_state.narrative_results)} narratives...")
            
            # Clear the progress message when done
            progress_container.empty()
            
            if not new_narratives_found:
                st.write("No new narratives found.")
            else:
                st.rerun()  # Only rerun if we found new narratives
    
    # Single display section for narratives
    if "narrative_results" in st.session_state and st.session_state.narrative_results:
        card_template = load_card_template(SEARCH_CARD_TEMPLATE_FILE)
        for narrative_idx, narrative in enumerate(st.session_state.narrative_results):
            card_html = card_template.replace("{{ title }}", narrative['title']) \
                                    .replace("{{ narrative }}", narrative.get('narrative', 'N/A')) \
                                    .replace("{{ community }}", narrative.get('community', 'N/A')) \
                                    .replace("{{ link }}", narrative['link']) \
                                    .replace("{{ content }}", narrative['content']) 
            st.markdown(card_html, unsafe_allow_html=True)

            unique_suffix = f"{narrative_idx}_{narrative['hash']}"
            
            # Create two columns with different widths (7:3 ratio)
            left_col, right_col = st.columns([0.8, 0.2])
            
            with left_col:
                # Create sub-columns for response controls with more balanced widths
                with st.form(key=f"response_form_{unique_suffix}"):
                    resp_col1, resp_col2 = st.columns([0.4, 0.6])
                    with resp_col2:
                        strategy = st.selectbox(
                            "Response Strategy",
                            options=list(RESPONSE_STRATEGIES.keys()),
                            key=f"strategy_{unique_suffix}",
                            label_visibility="collapsed"
                        )
                    with resp_col1:
                        submit_response = st.form_submit_button("Generate Response")
                        if submit_response:
                            with st.spinner('Generating response...'):
                                handle_generate_response(narrative, strategy)
                                st.success("Success! See Responses tab.")
            
            with right_col:

                if not is_archived(narrative["hash"]):
                        if st.button("Archive", key=f"archive_{narrative['hash']}"):
                            if save_narrative_artifact_to_sheets(narrative):
                                st.success("Saved to archive!")
                                st.rerun()
                else:
                    st.write("✓ Archived")

    else:
        st.write("No narrative artifacts yet. Please refer to the Listen tab to set search criteria first, then use the 'Find Narratives' button to retrieve narrative artifacts.")

with tab3:
    st.header("Responses")
    
    responses_data = load_narrative_responses()
    if not responses_data:
        st.write("No responses generated yet. Generate responses in the Search tab first.")
    else:
        # Add Clear All button
        if st.button("Clear All", type="secondary"):
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
                        if st.button("Save Response", key=f"save_{entry['id']}_{idx}"):
                            with st.spinner('Saving response to archive...'):
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
    
    st.write("Set your own Exa API key here")
    # Exa Configuration
    exa_api_key = st.text_input(
        "Exa API Key",
        value=st.session_state.get("exa_api_key", ""),
        type="password",
        help="If provided, this will override the API key in secrets.toml"
    )
    
    if st.button("Confirm"):
        if exa_api_key:
            st.session_state["exa_api_key"] = exa_api_key
            os.environ["EXA_API_KEY"] = exa_api_key
            st.success("API key saved successfully!")
        else:
            # Remove the custom API key if the input is empty
            if "exa_api_key" in st.session_state:
                del st.session_state["exa_api_key"]
            if "EXA_API_KEY" in os.environ:
                del os.environ["EXA_API_KEY"]
            st.info("Using default API key from secrets.toml")

