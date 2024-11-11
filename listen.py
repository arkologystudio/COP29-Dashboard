import json
import hashlib
from exa_py import Exa
from dotenv import load_dotenv
from datetime import datetime, timedelta
from openai import OpenAI
import streamlit as st
import requests
from bs4 import BeautifulSoup
from clients import get_exa_client, get_openai_client
import re
from typing import  Dict,  Optional, Iterable, Any


def invoke_identification_assistant(context):
    """Call the OpenAI API for each content context individually."""
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

def search_narrative_artifacts(days=7):
    """Search for narrative artifacts using Exa"""

    try:
        exa = get_exa_client()
        
        # Use session state directly instead of loading from file
        listening_tags = st.session_state.get('listening_tags', [])
        
        if not listening_tags:
            raise ValueError("No listening tags provided. Please add at least one tag to search.")

        tags = ", ".join(listening_tags)
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
    except ValueError as ve:
        st.error(f"Validation Error: {ve}")
        return []
    except RuntimeError as e:
        st.error(f"Error searching for narrative artifacts: {e}")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return []

def extract_urls(text: str, url_pattern: Optional[re.Pattern] = None) -> Iterable[str]:
    """
    Extracts all URLs from the given text using a regex pattern.

    Parameters:
    - text (str): The text to scan for URLs.
    - url_pattern (re.Pattern, optional): Precompiled regex pattern for URLs.

    Returns:
    - Iterable[str]: A generator of URLs found in the text.
    """
    return url_pattern.findall(text)


def scrape_html_from_url(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Optional[str]:
    """
    Fetches the final redirected URL if the provided URL is a Twitter t.co link by parsing the HTML.
    Otherwise, returns the HTML content of the URL.

    Parameters:
    - url (str): The URL of the web page to scrape.
    - headers (dict, optional): HTTP headers to include in the request.
    - timeout (int, optional): The maximum time to wait for a response, in seconds.

    Returns:
    - str: The final redirected URL or the HTML content of the page.
    - None: If an error occurs during the request.
    """
    if headers is None:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/58.0.3029.110 Safari/537.3'
            )
        }

    try:
        # Make the request without following redirects automatically
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=False)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

        # If the URL is a t.co link, attempt to parse the redirect URL from the HTML
        if re.match(r'^https?://t\.co/\w+', url):
            soup = BeautifulSoup(response.text, 'html.parser')

            # Attempt to find the meta refresh tag
            meta = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if meta:
                content = meta.get('content', '')
                match = re.search(r'URL=([^;]+)', content, re.IGNORECASE)
                if match:
                    redirected_url = match.group(1).strip()
                    return redirected_url

            # Attempt to find the JavaScript redirect
            script = soup.find('script')
            if script:
                match = re.search(r'location\.replace\(["\'](https?://[^"\']+)["\']\)', script.string or '')
                if match:
                    redirected_url = match.group(1).strip()
                    return redirected_url

            print(f"No redirect URL found in t.co link: {url}")
            return None

        # If not a t.co link, return the HTML content
        return response.text

    except requests.exceptions.Timeout:
        print(f"Error: The request to {url} timed out.")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - Status Code: {response.status_code}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request exception occurred: {req_err}")
    except ValueError as val_err:
        print(f"Value error: {val_err}")

    return None


def parse_narrative_artifact(exa_results: Iterable[Any]) -> Iterable[Dict[str, Any]]:
    """
    Parses narrative artifacts, extracts URLs from each result's text,
    resolves t.co redirects by parsing HTML content, scrapes HTML content from the final URLs,
    and enriches the data for LLM processing.

    Parameters:
    - exa_results (Iterable[Any]): An iterable of result objects containing text and title.

    Yields:
    - Dict[str, Any]: Parsed data enriched with scraped HTML and metadata.
    """
    url_pattern = re.compile(
        r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.'
        r'[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_\+.~#?&//=]*'
    )

    # Initialize processed hashes in session state if not already present
    if "processed_hashes" not in st.session_state:
        st.session_state.processed_hashes = set()

    for result in exa_results:
        if not hasattr(result, 'text') or not hasattr(result, 'title'):
            print("Result object missing 'text' or 'title' attribute.")
            continue

        urls = extract_urls(result.text, url_pattern)
        print("Found URLs: ", urls)

        urls_html_mapping = {}

        for url in urls:
            if url not in urls_html_mapping:  # Avoid duplicate scraping for the same URL
                original_url = url  # Keep track of the original URL
                final_url = url

                # Resolve t.co redirects by parsing HTML content
                if re.match(r'^https?://t\.co/\w+', url):
                    redirected_url = scrape_html_from_url(url)
                    if redirected_url:
                        final_url = redirected_url
                        # Handle multiple levels of t.co redirects
                        while re.match(r'^https?://t\.co/\w+', final_url):
                            print(f"Resolving second-level redirect for URL: {final_url}")
                            next_redirected_url = scrape_html_from_url(final_url)
                            if next_redirected_url and next_redirected_url != final_url:
                                final_url = next_redirected_url
                            else:
                                print(f"Failed to resolve further redirects for URL: {final_url}")
                                break
                    else:
                        print(f"Failed to resolve redirect for URL: {url}")
                        urls_html_mapping[original_url] = "Failed to resolve redirect."
                        continue
                print("url html mapping: ", urls_html_mapping) 
                # For non-t.co links or resolved URLs, fetch the HTML content
                html_content = scrape_html_from_url(final_url)
                soup = BeautifulSoup(html_content, 'html.parser')
                tags_to_extract = ['h1', 'h2', 'h3', 'h4', 'p']
                content = []
            
                # Find all specified tags while preserving their order
                for element in soup.find_all(tags_to_extract):
                    # Optionally, you can prefix headings to distinguish them
                    content.append(element.get_text())
                print("Content: ", content)
                if html_content and not re.match(r'^https?://(twitter|x)\.com/', final_url):
                    urls_html_mapping[original_url] = content
                elif re.match(r'^https?://(twitter|x)\.com/', final_url):
                    # If the final URL is still a Twitter/X URL, skip scraping
                    urls_html_mapping[original_url] = "Content is a Twitter/X page, not scraping HTML."
                elif final_url != original_url:
                    # If the final URL is different and not a Twitter/X URL, store the final URL
                    urls_html_mapping[original_url] = final_url
                else:
                    urls_html_mapping[original_url] = "Failed to retrieve HTML."

        # Generate a unique hash for each content based on the first 300 characters
        content_snippet = result.text[:300]
        content_hash = hashlib.md5(content_snippet.encode()).hexdigest()

        # Skip duplicates across multiple function calls
        if content_hash in st.session_state.processed_hashes:
            continue
        st.session_state.processed_hashes.add(content_hash)

        # Prepare context for the LLM
        llm_context = {
            "title": result.title,
            "content": result.text,
            "urls_html_mapping": urls_html_mapping  # Mapping between original URLs and their HTML or final URLs
        }


        try:
            parsed_data = invoke_identification_assistant(llm_context)
            if parsed_data:
                # Combine metadata from exa with the LLM response
                parsed_data["hash"] = content_hash  # Add the hash to parsed data
                parsed_data['link'] = result.url
                parsed_data['content'] = result.text
                parsed_data['links_out'] = list(urls_html_mapping.keys())  
                
                yield parsed_data  # Yield each parsed content individually with its hash
        except RuntimeError as e:
            print(f"Failed to process content: {e}")