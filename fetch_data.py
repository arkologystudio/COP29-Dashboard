from exa_py import Exa
from dotenv import load_dotenv
import os

load_dotenv()

exa = Exa(os.environ["EXA_API_KEY"])

def get_responding_data(query="COP29, climate change, sustainability"):
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
