import os
import json
from exa_py import Exa
from dotenv import load_dotenv
from datetime import datetime, timedelta
from openai import OpenAI

load_dotenv()

LISTENING_TAGS_FILE = "listening_tags.json"
LISTENING_RESPONSES_FILE = "listening_responses.json"

exa = Exa(os.environ["EXA_API_KEY"])
openai_api_key = os.environ["OPENAI_API_KEY"]
assistant_id = os.environ["ASSISTANT_ID"]
client = OpenAI(api_key=openai_api_key)
thread_id = None

def load_listening_tags():
    if os.path.exists(LISTENING_TAGS_FILE):
        with open(LISTENING_TAGS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return []

def load_listening_responses():
    if os.path.exists(LISTENING_RESPONSES_FILE):
        with open(LISTENING_RESPONSES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return []

def save_listening_responses(responses):
    with open(LISTENING_RESPONSES_FILE, "w", encoding="utf-8") as file:
        json.dump(responses, file, indent=4)
        
import json

import json

def parse_assistant_data(sync_cursor_page):
    messages_data = sync_cursor_page.data
    contents = []

    for message in messages_data:
        if message.role == "assistant":
            for content_block in message.content:
                try:
                    message_content = json.loads(content_block.text.value)
                    if isinstance(message_content, list):
                        contents.extend(message_content)
                except json.JSONDecodeError:
                    print("Content is not in JSON format or has invalid JSON structure.")

    formatted_string = json.dumps(contents)
    return formatted_string



def call_chatgpt_api(responding_data):
    global thread_id
    if thread_id == None:
        thread = client.beta.threads.create()
        thread_id = thread.id
    
    json_data = json.dumps(responding_data)
    
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content= json_data + ""
    )
            
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
        instructions="""Process these incoming tweets. Extract the following from each:
        1. Title: If none is provided, generate one based on the content.
        2. Narrative: Identify the overarching narrative of the content. For example, "techno-solutionism."
        3. Link: The link to the post.
        4. Content: The content of the post.

        Reply with a like-for-like array of the data you receive and nothing else. This array should be in the format of a json array but should be in raw text. Each post should be formatted as:

        {
            "title": "some title",
            "narrative": "some narrative",
            "link": "some link",
            "content": "some content"
        }"""
    )
    
    if run.status == 'completed': 
        messages = client.beta.threads.messages.list(
        thread_id=thread.id
        )
        print(messages)
    else:
        print(run.status)
        raise f"An error occurred: {str(run.status)}"
    
    parsed_messages = parse_assistant_data(messages)
    
    print(f"parsed messages: {parsed_messages}")

    return parsed_messages

def get_responding_data(days):
    tags = load_listening_tags()
    natural_query = ", ".join(tags)
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    response = exa.search_and_contents(
        natural_query,
        num_results=5,
        use_autoprompt=True,
        include_domains=["x.com"],
        category="tweet",
        text={"max_characters": 500},
        highlights=True,
        start_published_date=start_date
    )

    responding_data = []

    for result in response.results:
        responding_data.append({
            "title": result.title if result.title else "No title",
            "link": result.url,
            "content": result.text[:200]
        })

    processed_data = call_chatgpt_api(responding_data)
    
    if processed_data.startswith("```json"):
        processed_data = processed_data[7:-3].strip()

    try:
        new_responses = json.loads(processed_data)
    except json.JSONDecodeError:
        raise ValueError("Incorrect format returned from ChatGPT. Try again.")
    
    old_responses = load_listening_responses()
    all_responses = new_responses + old_responses
    save_listening_responses(all_responses)

    return all_responses