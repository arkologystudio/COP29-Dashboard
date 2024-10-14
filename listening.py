import os
import json
from exa_py import Exa
from dotenv import load_dotenv

load_dotenv()

LISTENING_TAGS_FILE = "listening_tags.json"
LISTENING_RESPONSES_FILE = "listening_responses.json"

exa = Exa(os.environ["EXA_API_KEY"])

def load_listening_tags():
    if os.path.exists(LISTENING_TAGS_FILE):
        with open(LISTENING_TAGS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return []

def save_listening_responses(responses):
    with open(LISTENING_RESPONSES_FILE, "w", encoding="utf-8") as file:
        json.dump(responses, file, indent=4)

def get_responding_data():
    tags = load_listening_tags()

    natural_query = ", ".join(tags)

    response = exa.search_and_contents(
        natural_query,
        num_results=5,
        use_autoprompt=True,
        include_domains=["x.com"],
        category="tweet",
        text={"max_characters": 500},
        highlights=True
    )

    responding_data = []

    for result in response.results:
        responding_data.append({
            "title": result.title if result.title else "No title",
            "link": result.url,
            "content": result.text[:200]
        })

    save_listening_responses(responding_data)

    return responding_data
