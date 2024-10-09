from exa_py import Exa
from dotenv import load_dotenv
import os

load_dotenv()

exa = Exa(os.environ["EXA_API_KEY"])

LISTENING_TAGS_FILE = "listening_tags.txt"

def load_listening_tags():
    if os.path.exists(LISTENING_TAGS_FILE):
        with open(LISTENING_TAGS_FILE, "r") as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    return []

def get_responding_data(query=None):
    #Think about this
    if query is None:
        listening_tags = load_listening_tags()
        if listening_tags:
            query = ", ".join(listening_tags)
        else:
            query = "COP29, climate change, sustainability" 

    # print(query)

    response = exa.search_and_contents(
        query,
        num_results=5,
        use_autoprompt=True,
        include_domains=["x.com"],
        category="tweet",
        text={"max_characters": 500},
        highlights=True
    )

    responding_data = []
    for result in response.results:
        narrative = {
            "title": result.title or "No Title",
            "link": result.url,
            "content": result.text[:200] + "..." if result.text else "No Content",
        }
        responding_data.append(narrative)
    
    return responding_data

# Sample function to print results to console (for testing)
if __name__ == "__main__":
    data = get_responding_data()
    for item in data:
        print(f"Title: {item['title']}")
        print(f"Link: {item['link']}")
        print(f"Content: {item['content']}")
        print("---")
