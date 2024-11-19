import json
import hashlib
from exa_py import Exa
from dotenv import load_dotenv
from datetime import datetime, timedelta
from openai import OpenAI
import streamlit as st

from clients import get_exa_client, get_openai_client

def invoke_identification_assistant(context):
    """Call the OpenAI API for each content context individually."""
    try:
        client = get_openai_client()  # Get client when needed
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=json.dumps(context)
        )

        assistant_id = st.secrets["openai"]["narrative_identification_assistant_id"] 

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id,
        )
        
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            return parse_assistant_data(messages)
        else:
            raise RuntimeError(f"An error occurred: {run.status}. {run.last_error}")
            
    except Exception as e:
        print(f"Error in invoke_identification_assistant: {str(e)}")
        raise RuntimeError(f"An error occurred: {e}")

def parse_assistant_data(messages):
    """Parse assistant messages and return JSON-formatted content."""
    for message in messages.data:
        if message.role == "assistant":
            try:
                return json.loads(message.content[0].text.value)
            except (json.JSONDecodeError, IndexError):
                print("Error parsing assistant message content.")
    return {}

import hashlib
import streamlit as st

def search_narrative_artefacts(days=7):
    """Search for narrative artefacts using Exa"""

    try:
        exa = get_exa_client()
        
        # Use session state directly instead of loading from file
        tags = ", ".join(st.session_state.listening_tags)
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        response = exa.search_and_contents(
            tags, 
            num_results=st.session_state.num_results, 
            type=st.session_state.search_type, 
            use_autoprompt=st.session_state.use_autoprompt, 
            include_domains=["x.com"],
            category="tweet", 
            text=True, 
            highlights=False,
            start_published_date=start_date,
            livecrawl=st.session_state.livecrawl 
        )

        # Remove duplicates from search results based on URL
        seen_urls = set()
        unique_results = []
        for result in response.results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        response.results = unique_results

        return response.results
    except RuntimeError as e:
        print(f"Error searching for narrative artefacts: {e}")
        return []
def parse_narrative_artefact(exa_results):
    """Parse narrative artefacts using the Narrative Identification Assistant."""
    try:
        print("Starting to parse narrative artefacts...")
        
        if "processed_hashes" not in st.session_state:
            st.session_state.processed_hashes = set()
            print("Initialized processed_hashes in session state")
        
        for result in exa_results:
            print(f"Processing result with title: {result.title}")

            # Generate a unique hash for each content
            content_hash = hashlib.md5(result.text[:300].encode()).hexdigest()
            print(f"Generated hash: {content_hash}")
            
            # Skip duplicates across multiple function calls
            if content_hash in st.session_state.processed_hashes:
                print(f"Skipping duplicate content with hash: {content_hash}")
                continue
            st.session_state.processed_hashes.add(content_hash)
            
            llm_context = {
                "title": result.title,
                "content": result.text
            }
            print(f"Created LLM context with title: {result.title}")
            
            try:
                print("Calling identification assistant...")
                parsed_data = invoke_identification_assistant(llm_context)
                if parsed_data:
                    print("Successfully received parsed data from assistant")
                    # Combine metadata from exa with the LLM response
                    parsed_data["hash"] = content_hash  # Add the hash to parsed data
                    parsed_data['link'] = result.url
                    parsed_data['content'] = result.text
                    print(f"Yielding parsed data for content with hash: {content_hash}")
                    yield parsed_data  # Yield each parsed content individually with its hash
                else:
                    print("Warning: identification assistant returned empty result")
            except RuntimeError as e:
                print(f"Failed to process content with hash {content_hash}. Error: {str(e)}")
                print(f"LLM context that caused error: {llm_context}")
    except RuntimeError as e:
        print(f"Critical error in parse_narrative_artefact: {str(e)}")
        print(f"Full error context: {e.__class__.__name__}: {str(e)}")
        raise RuntimeError(f"Failed to parse narrative artefacts: {str(e)}")


