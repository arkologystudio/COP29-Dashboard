import streamlit as st
import os
from database import setup_google_sheets, get_sheets
from listen import parse_narrative_artefact, search_narrative_artefacts
import datetime
from config import SEARCH_CARD_TEMPLATE_FILE, RESPONSE_STRATEGIES, VOICES
from respond import generate_response
from typed_dicts import NarrativeResponse, Response, OriginalPost
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
    
def handle_generate_thread(narrative, response_idx):
    try:    
        link_assistant_id = st.secrets["openai"]["link_assistant_id"]

        thread_data = load_thread_data_from_sheets()


        # Filter out the 'Link' property from thread data
        openai_thread_data = [{k: v for k, v in thread.items() if k != 'Link'} for thread in thread_data]
        link_llm_context = {
            "narrative": narrative['responses'][response_idx]['content'],
            "thread_data": openai_thread_data
        }

        link_res = generate_response(link_assistant_id, link_llm_context)
        
        if link_res != 'NULL' and link_res.isdigit():
            thread = next((thread for thread in thread_data if thread['Thread'] == ('Thread ' + str(link_res))), None)
        else:
            thread = None
        
        # Add thread to narrative state
        if thread:
            # Update the narrative_responses in session state
            if 'narrative_responses' in st.session_state:
                for idx, resp_entry in enumerate(st.session_state.narrative_responses):
                    if resp_entry.get("id") == narrative["id"]:
                        st.session_state.narrative_responses[idx]["thread"] = thread
                        break
                st.success("Thread generated successfully!")
            else:
                st.error("No narrative_responses found in session state.")
        else:
            st.warning("No matching thread found")
            
    except Exception as e:
        st.error(f"Failed to generate thread: {str(e)}")



def handle_generate_hashtags(entry):
    """Generate and update hashtags for a given response entry."""
    try:
        # Check for required fields
        if 'original_post' not in entry:
            st.error("Entry is missing 'original_post'.")
            return
        if 'content' not in entry['original_post']:
            st.error("Entry is missing 'content' in 'original_post'.")
            return
        if 'responses' not in entry:
            st.error("Entry is missing 'responses'.")
            return
        if 'id' not in entry:
            st.error("Entry is missing 'id'.")
            return

        # Access the content from the original post
        original_content = entry['original_post']['content']
        
        # Access the responses
        responses = entry['responses']

        # Prepare context for hashtag generation
        hashtag_assistant_id = st.secrets["openai"]["hashtag_assistant_id"]
        
        # Ensure that hashtag_assistant_id is a string
        if not isinstance(hashtag_assistant_id, str):
            st.error("Invalid assistant ID type. Expected a string.")
            return
        
        hashtag_map = load_hashtag_data_from_sheets()
        hashtag_llm_context = {
            "context": {
                "original post": original_content, 
                "responses": [response['content'] for response in responses]  # Collecting all response contents
            },
            "hashtag_map": hashtag_map
        }

        hashtag_res = generate_response(hashtag_assistant_id, hashtag_llm_context)
        if hashtag_res:
            # Parse hashtag_res into list
            try:
                # Assuming hashtag_res is a string of hashtags separated by spaces or commas
                hashtags = [hashtag.strip() for hashtag in hashtag_res.replace(',', ' ').split() if hashtag.startswith('#')]
            except:
                hashtags = []  # Fallback if parsing fails
                
            # Update the narrative_responses in session state
            if 'narrative_responses' in st.session_state:
                for idx, resp_entry in enumerate(st.session_state.narrative_responses):
                    if resp_entry.get("id") == entry["id"]:
                        st.session_state.narrative_responses[idx]["hashtags"] = hashtags
                        break
            else:
                st.error("No narrative_responses found in session state.")
            
            st.success("Hashtags generated successfully!")



    except Exception as e:
        st.error(f"Failed to generate hashtags: {str(e)}")

def handle_generate_response(narrative: dict, strategy: str, voice: str):
    """Handle response generation for a narrative with specific strategy."""
    assistant_id = RESPONSE_STRATEGIES[strategy]
    llm_context = {
        "title": narrative['title'],
        "narrative": narrative['narrative'],
        "community": narrative['community'],
        "content": narrative['content']
    }
    res = generate_response(assistant_id, llm_context)

    if not res:
        st.error("Failed to generate a response.")
        return

    if voice != "Default":
        voice_assistant_id = VOICES[voice]
        llm_context = narrative['content']
        res = generate_response(voice_assistant_id, res)

    # Create response object with strategy metadata
    response_obj = {
        "content": res,
        "strategy": strategy,
        "voice": voice,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Create response entry with all narrative data
    response_entry: NarrativeResponse = {
        "id": narrative["hash"],  # Standardizing 'id' to be the same as 'hash'
        "original_post": {
            "title": narrative["title"],
            "narrative": narrative["narrative"],
            "community": narrative.get("community", "N/A"),
            "link": narrative["link"],
            "content": narrative["content"],
            "date": datetime.date.today().strftime("%Y-%m-%d"),
        },
        "responses": [response_obj],
        "hashtags": narrative.get("hashtags", []),  # Ensure hashtags are included
        "thread": narrative.get("thread", "")        # Ensure thread is included
    }

    # Initialize responses in session state if not exists
    if 'narrative_responses' not in st.session_state:
        st.session_state.narrative_responses = []
    
    # Check if entry with this ID exists
    existing_entry = next((item for item in st.session_state.narrative_responses 
                          if item.get("id") == response_entry["id"]), None)
    if existing_entry:
        # Append new response to existing entry
        existing_entry["responses"].append(response_obj)
        existing_entry["hashtags"] = response_entry["hashtags"]  # Update hashtags
        existing_entry["thread"] = response_entry["thread"]      # Update thread
    else:
        # Add new entry
        st.session_state.narrative_responses.append(response_entry)
    
    st.success("Response generated successfully! Check the Responses tab.")

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
        
        # Prepare the row data, ensuring all fields are included
        hashtags = response_data.get("hashtags", [])

        # Join hashtags into a single string
        hashtags_string = ' '.join(hashtags) if isinstance(hashtags, list) else hashtags
        
        # Get the thread and ensure it's a string
        thread = response_data.get("thread", "")
        if isinstance(thread, dict):
            # If thread is a dictionary, convert it to a string representation
            thread = f"Thread: {thread.get('Topic', 'N/A')} - Link: {thread.get('Link', 'N/A')}"
        
        # Prepare the row data, ensuring all fields are included in the correct order
        row_data = [
            response_data.get("id", ""),  # ID
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Date
            response_data["original_post"].get("title", ""),  # Title
            response_data["original_post"].get("content", ""),  # Original Post
            response_data["original_post"].get("link", ""),  # Link
            response_data["responses"][idx].get("content", ""),  # Response
            response_data["responses"][idx].get("strategy", ""),  # Strategy
            hashtags_string,  # Hashtags
            thread,           # Thread
            False,            # Posted?
            0,                # View Count (at time of response)
            0,                # Like Count (at time of response)
            0                 # Retweet Count (at time of response)
        ]
        

        responses_sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Failed to save to archive: {str(e)}")
        return False
    
def load_thread_data_from_sheets():
    """Load data from Google Sheets archive."""
    try:
        sheets = get_sheets()
        if not sheets:
            st.error("Could not access worksheets")
            return None
        thread_sheet = sheets['threads']      
        thread_records = thread_sheet.get_all_records()
        return thread_records
    except Exception as e:
        st.error(f"Failed to load from archive: {str(e)}")
        return None

def load_hashtag_data_from_sheets():
    """Load data from Google Sheets archive."""         
    try:
        sheets = get_sheets()
        if not sheets:
            st.error("Could not access worksheets")
            return None
        hashtag_sheet = sheets['hashtags']
        hashtag_records = hashtag_sheet.get_all_records()
        return hashtag_records
    except Exception as e:
        st.error(f"Failed to load from archive: {str(e)}")
        return None

def save_narrative_artefact_to_sheets(narrative_data):
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
            narrative_data.get("hashtags", ""),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestam     
        ]
        
        # Append the row
        narrative_sheet.append_row(row_data)
        
        # Mark as archived in session state
        if 'archived_narratives' not in st.session_state:
            st.session_state.archived_narratives = set()
        st.session_state.archived_narratives.add(narrative_data.get("hash"))
        
        # Get the updated narrative data from sheets to ensure we have latest version
        updated_narrative = narrative_sheet.find(narrative_data["hash"])
        if updated_narrative:
            row = narrative_sheet.row_values(updated_narrative.row)
            return {
                "hash": row[0],
                "title": row[1], 
                "narrative": row[2],
                "community": row[3],
                "link": row[4],
                "content": row[5],
                "hashtags": row[6]
            }
        return updated_narrative
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
        
        # Main form inputs
        temp_num_results = st.slider(
            "Number of results:", 
            min_value=1, 
            max_value=10, 
            value=st.session_state.get('num_results', 5),
            step=1
        )

        listening_data_str = "\n".join(load_listening_tags())
        temp_user_input = st.text_area(
            "Enter list of search phrases (one per line):", 
            listening_data_str, 
            placeholder="e.g.\nCarbon storage and capture devices\nCarbon credit markets\nInvestment in clean energy", 
            height=160,
        )
        
        temp_days_input = st.number_input(
            "Enter number of days in the past to search:", 
            min_value=0, 
            max_value=365, 
            value=st.session_state.get('days_input', 1), 
            step=1
        )

        # Advanced parameters in expander
        with st.expander("Advanced Search Parameters"):

            temp_use_autoprompt = st.checkbox(
                "Use autoprompt",
                value=st.session_state.get('use_autoprompt', True),
                help="Automatically enhance the search query to improve results"
            )

            temp_search_type = st.selectbox(
                "Search type:",
                options=["neural", "keyword", "auto"],
                index=["neural", "keyword", "auto"].index(st.session_state.get('search_type', 'neural')),
                help="neural: semantic search using embeddings, keyword: exact text match, auto: automatically choose best method"
            )

            temp_livecrawl = st.selectbox(
                "Live crawl:",
                options=[None, "always"],
                index=[None, "always"].index(st.session_state.get('livecrawl', None)),
                help="None: use cached results, always: fetch fresh results from source"
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
            
            st.success("Listening model updated successfully")

# Results
with tab2:
    
    st.header("Search & Review")
    st.write("Search & review retrieved narrative artefacts")


    # Add checkbox for filtering insufficient context
    show_sufficient_context = st.checkbox(
        "Show narratives with sufficient context only",
        value=False,
        help="Filter to show only narratives that have been flagged as having sufficient context"
    )

    if st.button("Find Narratives"):
        # Initialize results list if it doesn't exist
        if "narrative_results" not in st.session_state:
            st.session_state.narrative_results = []
        
        progress_container = st.empty()
        with st.spinner('Searching narratives...'):
            # First search for artefacts
            search_results = search_narrative_artefacts(days=st.session_state.days_input)
            
            # Track new narratives found in this search
            new_narratives_found = False
            
            # Then parse each artefact
            for narrative in parse_narrative_artefact(search_results):
                # Check if this narrative is already in results
                if not any(item.get("hash") == narrative["hash"] for item in st.session_state.narrative_results):
                    # Add insufficient_context flag to narrative
                    narrative["insufficient_context"] = len(narrative.get("content", "").strip()) < 100
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

    # Filter results based on insufficient context checkbox
    filtered_results = []
    if "narrative_results" in st.session_state:
        if show_sufficient_context:
            filtered_results = [n for n in st.session_state.narrative_results if n.get("narrative") != "Insufficient Context"]
        else:
            filtered_results = st.session_state.narrative_results

    # Single display section for narratives
    if filtered_results:
        card_template = load_card_template(SEARCH_CARD_TEMPLATE_FILE)
        for narrative_idx, narrative in enumerate(filtered_results):
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
                    resp_col1, resp_col2 = st.columns(2)
                    with resp_col1:
                        strategy = st.selectbox(
                            "Strategy",
                            options=list(RESPONSE_STRATEGIES.keys()),
                            key=f"strategy_{unique_suffix}"
                        )
                    with resp_col2:
                        voice = st.selectbox(
                            "Voice", 
                            options=list(VOICES.keys()),
                            key=f"voice_{unique_suffix}"
                        )
                    submit_response = st.form_submit_button("Generate Response")
                    if submit_response:
                        with st.spinner('Generating response...'):
                            handle_generate_response(narrative, strategy, voice)
            with right_col:

                if not is_archived(narrative["hash"]):
                        if st.button("Archive", key=f"archive_{narrative['hash']}"):
                            if save_narrative_artefact_to_sheets(narrative):
                                st.success("Saved to archive!")
                                st.rerun()
                else:
                    st.write("✓ Archived")

    else:
        st.write("No narrative artefacts yet. Please refer to the Listen tab to set search criteria first, then use the 'Find Narratives' button to retrieve narrative artefacts.")

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
                        # Editable text area for response content
                        response_content = st.text_area(f"Response {idx + 1} (Strategy: {response['strategy']})", 
                                                         value=response['content'], 
                                                         height=200, 
                                                         key=f"response_edit_{entry['id']}_{idx}")
                        
                        # Button to update the response content in the session state
                        if st.button("Update Response", key=f"update_{entry['id']}_{idx}"):
                            if 'narrative_responses' in st.session_state:
                                for i, resp_entry in enumerate(st.session_state.narrative_responses):
                                    if resp_entry.get("id") == entry["id"]:
                                        st.session_state.narrative_responses[i]["responses"][idx]["content"] = response_content
                                        st.rerun()
                                        break
                                st.success("Response content updated!")

                            else:
                                st.error("No narrative_responses found in session state.")
                            

                       
                        # Display suggested hashtags

                        st.markdown('**Suggested Hashtags**')

                        if 'hashtags' in entry and entry['hashtags']:

                            # Flatten the list of hashtags if it's a list of lists
                            flat_hashtags = [hashtag for sublist in entry['hashtags'] for hashtag in sublist] if isinstance(entry['hashtags'][0], list) else entry['hashtags']
                            st.markdown(" ".join(flat_hashtags))  # Ensure hashtags are displayed
                        else:
                            with st.form(key=f"hashtag_form_{entry['id']}_{idx}"):
                                st.markdown("No hashtags found")
                                if st.form_submit_button("Generate Hashtags"):
                                        handle_generate_hashtags(entry)
                                        st.rerun()

                        st.markdown("**Associated Thread**")
                        if 'thread' in entry and entry['thread']:
                            st.markdown(entry['thread']['Topic'])
                            st.markdown(entry['thread']['Link'])
                        else:
                             with st.form(key=f"thread_form_{entry['id']}_{idx}"):
                                st.markdown("No thread found")
                                if st.form_submit_button("Generate Thread"):
                                        handle_generate_thread(entry, idx)
                                        st.rerun()
                        # Button to save the updated response to sheets
                        if st.button("Save Response to Sheets", key=f"save_{entry['id']}_{idx}"):
                            with st.spinner('Saving response to archive...'):
                                save_response_to_sheets(entry, idx)  # Save to sheets
                                st.success("Response saved to archive!")
# Archive:
with tab4: 
    st.header("Archive")
    st.write("View the archived responses in the Google Sheet:")
    
    # Add a checkbox to filter by posted value
    filter_posted = st.checkbox("Show Posted Responses", value=True)

    st.markdown(f"[See archived responses](https://docs.google.com/spreadsheets/d/1y3rOqpZ1chq7SNdxRIdeHyhi7Kp0YL5UGbbUKDkjA-M/edit?usp=sharing)", unsafe_allow_html=True)

    
    
    try:
        # Get fresh connection to sheets
        sheets = get_sheets()
        if not sheets:
            st.error("Could not access worksheets")
        else:
            responses_sheet = sheets['responses']
            
            # Define expected headers
            expected_headers = ['Title', 'Original Post', 'Response', 'Strategy', 'Link', 'Date', 'Hashtags', 'Thread']
            responses = responses_sheet.get_all_records(expected_headers=expected_headers)
            
            if not responses:
                st.write("No archived responses found.")
            else:
                # Get count of archived responses
          
                for index, response in enumerate(responses):  # Use enumerate to get the index
                    # Filter responses based on the posted checkbox
                    posted = response['Posted'] == True or response['Posted'] == 'TRUE'
                    if filter_posted and posted:
                        continue  # Skip posted responses if the checkbox is checked
                    
                    with st.expander(f"🗂️ {response.get('Title', 'Untitled')}", expanded=False):
                        st.markdown("**Original Post:**")
                        st.write(response.get('Original Post', 'No content'))
                        
                        st.markdown("**Response:**") 
                        st.write(response.get('Response', 'No response'))
                        st.write(response.get('Hashtags', ''))
                        # Extract thread link if p  resent
                        thread = response.get('Thread', '')
                        if thread:
                            # Check if thread contains "Link:" and extract the URL
                            if 'Link:' in thread:
                                thread_parts = thread.split('Link:')
                                thread_text = thread_parts[0].strip()
                                thread_link = thread_parts[1].strip()
                                st.write(f"{thread_link}")
                  

                        st.markdown("**Hashtags:**")
                        st.write(response.get('Hashtags', 'No hashtags'))
                        st.markdown("**Thread:**")
                        st.write(response.get('Thread', 'No thread'))
                        st.markdown("**Strategy:**")
                        st.write(response.get('Strategy', 'No strategy'))
                        
                        st.markdown("**Source:**")
                        if response.get('Link'):
                            st.markdown(f"[Source Link]({response['Link']})")
                        else:
                            st.write("No source link")
                            
                        st.markdown("**Archived on:**")
                        st.write(response.get('Date', 'No date'))
                        
                        st.markdown("---")
                        st.markdown("**Approved By:**")
                        

                        st.markdown("---")  
                        # Posted status
                        st.markdown("**Posted Status:**")
                        
                        
                        if posted:
                            st.info("✓ This response has been posted")
                        else:
                            st.warning("⚠ This response has not been posted yet")
                            with st.form(key=f"post_metrics_{response.get('Date')}_{index}"):
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    views = st.number_input("Views", min_value=0, value=0)
                                with col2:
                                    likes = st.number_input("Likes", min_value=0, value=0)
                                with col3:
                                    retweets = st.number_input("Retweets", min_value=0, value=0)
                                with col4:
                                    comments = st.number_input("Comments", min_value=0, value=0)
                                submitted = st.form_submit_button("Submit Metrics")
                                if submitted:
                                    # Update metrics columns (adjusted indices)
                                    responses_sheet.update_cell(responses.index(response) + 2, 16, views)  # Views
                                    responses_sheet.update_cell(responses.index(response) + 2, 17, likes)  # Likes
                                    responses_sheet.update_cell(responses.index(response) + 2, 18, retweets)  # Retweets
                                    responses_sheet.update_cell(responses.index(response) + 2, 19, comments)  # Comments
                                    st.success("Metrics updated!")
                        if st.button("Mark as Posted", key=f"mark_posted_{response.get('Date')}_{index}", disabled=posted):
                            # Update the Posted? column (column 14)
                            responses_sheet.update_cell(responses.index(response) + 2, 15, True)
                            st.success("Marked as posted!")
                            st.rerun()
                            
    except Exception as e:
        st.error(f"Error loading archived responses: {str(e)}")
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

