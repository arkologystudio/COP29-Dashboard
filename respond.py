import os
import json

from dotenv import load_dotenv
from datetime import datetime, timedelta
from openai import OpenAI
import streamlit as st

# Load environment variables
load_dotenv()

def get_openai_client():
    """Get or create OpenAI client instance"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)

def invoke_assistant(context, assistant_id):
    """Invoke the LLM Assistant with the given context."""
    client = get_openai_client()  # Get client when needed
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
        return parse_assistant_message(messages)
    else:
        raise RuntimeError(f"An error occurred: {run.status}")

def parse_assistant_message(messages):
    """Parse assistant messages."""
    for message in messages.data:
        if message.role == "assistant":
            try:
                return message.content[0].text.value
            except (json.JSONDecodeError, IndexError):
                print("Error parsing assistant message content.")
    return {}


def generate_response(narrative, assistant_id):
    """Construct the context and invoke the assistant."""
        
    llm_context = {
        "title": narrative['title'],
        "narrative": narrative['narrative'],
        "community": narrative['community'],
        "content": narrative['content']
    }
        
    try:
        response = invoke_assistant(llm_context, assistant_id)
        if response:
            return response
            
    except RuntimeError as e:
        print(f"Failed to generate response: {e}")


