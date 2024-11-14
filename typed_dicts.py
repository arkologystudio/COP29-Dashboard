
from typing import TypedDict, List, Optional





class Response(TypedDict):
    content: str
    strategy: str
    voice: str
    timestamp: str

class OriginalPost(TypedDict):
    title: str
    narrative: str
    community: str
    link: str
    content: str
    date: str

class NarrativeResponse(TypedDict):
    id: str
    original_post: OriginalPost
    responses: List[Response]
    hashtags: List[str]
    thread: Optional[dict]