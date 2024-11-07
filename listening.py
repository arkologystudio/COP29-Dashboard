import hashlib
import os
import json
from exa_py import Exa
from dotenv import load_dotenv
from datetime import datetime, timedelta
from openai import OpenAI
import streamlit as st


# Load environment variables
load_dotenv()
exa = Exa(os.getenv("EXA_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID")

# File paths
LISTENING_TAGS_FILE = "listening_tags.json"

def load_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def call_chatgpt_api(context):
    """Call the OpenAI API for each tweet context individually."""
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

def get_responding_data(days):
    """Fetch and parse social media posts based on listening tags, yielding each parsed tweet individually."""
    tags = ", ".join(load_json_file(LISTENING_TAGS_FILE))
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    response = exa.search_and_contents(
        tags, num_results=5, use_autoprompt=True, include_domains=["x.com"],
        category="tweet", text={"max_characters": 500}, highlights=True,
        start_published_date=start_date
    )
    
    if "processed_hashes" not in st.session_state:
        st.session_state.processed_hashes = set()
    
    for result in response.results:
        # Generate a unique hash for each tweet content
        content_hash = hashlib.md5(result.text[:300].encode()).hexdigest()
        
        # Skip duplicates across multiple function calls
        if content_hash in st.session_state.processed_hashes:
            continue
        st.session_state.processed_hashes.add(content_hash)
        
        tweet_context = {
            "title": result.title or "No title",
            "link": result.url,
            "content": result.text
        }
        
        try:
            parsed_data = call_chatgpt_api(tweet_context)
            if parsed_data:
                parsed_data["hash"] = content_hash  # Add the hash to parsed data
                yield parsed_data  # Yield each parsed tweet individually with its hash
        except RuntimeError as e:
            print(f"Failed to process tweet: {e}")


