import hashlib
import os
import json
from exa_py import Exa
from dotenv import load_dotenv
from datetime import datetime, timedelta
from openai import OpenAI
import streamlit as st
from config import LISTENING_TAGS_FILE, NARRATIVE_IDENTIFICATION_ASSISTANT

# Load environment variables
load_dotenv()
exa = Exa(os.getenv("EXA_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = NARRATIVE_IDENTIFICATION_ASSISTANT

def load_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def call_chatgpt_api(context):
    """Call the OpenAI API for each content context individually."""
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=json.dumps(context)
    )
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )
    
    if run.status == 'completed':
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        return parse_assistant_data(messages)
    else:
        raise RuntimeError(f"An error occurred: {run.status}")

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

def parse_narrative_artifact(days):
    """Fetch and parse social media posts based on listening tags, yielding each parsed content individually."""
    tags = ", ".join(load_json_file(LISTENING_TAGS_FILE))
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    response = exa.search_and_contents(
        tags, num_results=5, use_autoprompt=True, include_domains=["x.com"],
        category="content", text={"max_characters": 500}, highlights=True,
        start_published_date=start_date, 
    )

    # Remove duplicates from search results based on URL
    seen_urls = set()
    unique_results = []
    for result in response.results:
        if result.url not in seen_urls:
            seen_urls.add(result.url)
            unique_results.append(result)
    response.results = unique_results

    
    if "processed_hashes" not in st.session_state:
        st.session_state.processed_hashes = set()
    
    for result in response.results:

        print("Result: ",result)

        # Generate a unique hash for each content
        content_hash = hashlib.md5(result.text[:300].encode()).hexdigest()
        
        # Skip duplicates across multiple function calls
        if content_hash in st.session_state.processed_hashes:
            continue
        st.session_state.processed_hashes.add(content_hash)
        
        llm_context = {
            "title": result.title,
            "content": result.text
        }
        
        try:
            parsed_data = call_chatgpt_api(llm_context)
            if parsed_data:
                # Combine metadata from exa with the LLM response
                parsed_data["hash"] = content_hash  # Add the hash to parsed data
                parsed_data['link'] = result.url
                #parsed_data['content'] = result.text
                parsed_data['favorite_count'] = getattr(result, 'favorite_count', '-')
                parsed_data['reply_count'] = getattr(result, 'reply_count', '-') 
                parsed_data['quote_count'] = getattr(result, 'quote_count', '-')
                parsed_data['retweet_count'] = getattr(result, 'retweet_count', '-')
                yield parsed_data  # Yield each parsed content individually with its hash
        except RuntimeError as e:
            print(f"Failed to process content: {e}")


