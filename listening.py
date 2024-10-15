import os
import json
import openai
from exa_py import Exa
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

LISTENING_TAGS_FILE = "listening_tags.json"
LISTENING_RESPONSES_FILE = "listening_responses.json"

exa = Exa(os.environ["EXA_API_KEY"])
openai.api_key = os.environ["OPENAI_API_KEY"]

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

def call_chatgpt_api(responding_data):
    prompt = """
    Process these incoming tweets. Extract the following from each:
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
    }
    """

    messages = [
        {"role": "system", "content": """
            You are data processor. You process incoming tweets.Extract the following from each:
            1. Title: If none is provided, generate one based on the content.
            2. Narrative: Identify the overarching narrative of the content. For example, "techno-solutionism."
            3. Link: The link to the post.
            4. Content: The content of the post.

            Reply with just a like-for-like array of the data you receive and nothing else. This array should be in the format of a json array but should be in raw text. Each post should be formatted as:

            {
                "title": "some title",
                "narrative": "some narrative",
                "link": "some link",
                "content": "some content"
            }
         """},
        {"role": "user", "content": prompt + json.dumps(responding_data)}
    ]

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    
    print(response.choices[0].message.content)

    return response.choices[0].message.content

def get_responding_data():
    tags = load_listening_tags()
    natural_query = ", ".join(tags)
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    response = exa.search_and_contents(
        natural_query,
        num_results=5,
        use_autoprompt=True,
        include_domains=["x.com"],
        category="tweet",
        text={"max_characters": 500},
        highlights=True,
        start_published_date=one_week_ago
    )
    
    #TODO: HANDLE FORMATTING ERRORS IN RESPONSE OBJECT FROM CHATGPT API

    responding_data = []

    for result in response.results:
        responding_data.append({
            "title": result.title if result.title else "No title",
            "link": result.url,
            "content": result.text[:200]
        })

    processed_data = call_chatgpt_api(responding_data)
    new_responses = json.loads(processed_data)
    old_responses= load_listening_responses()
    all_responses = new_responses + old_responses
    save_listening_responses(all_responses)

    return all_responses

