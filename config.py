# Assistant IDs for OpenAI
NARRATIVE_IDENTIFICATION_ASSISTANT = "asst_nn5V0Kytzv90U3qcdmfVcFBg"


# File paths
LISTENING_TAGS_FILE = "data/listening_tags.json"
LISTENING_RESULTS_FILE = "data/listening_responses.json"
NARRATIVE_RESPONSES_FILE = "data/narrative_responses.json"

SEARCH_CARD_TEMPLATE_FILE = "templates/search_result_card.html"

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'cop29-resources-archive-sheet-b1f6dc1221fa.json'
SHEET_ID = '1y3rOqpZ1chq7SNdxRIdeHyhi7Kp0YL5UGbbUKDkjA-M'

# Assistant ID mappings for different response strategies
RESPONSE_STRATEGIES = {
    "Truth Query": "asst_MqyR55qRVdZJPyodhQ4wpVqP",
    "Perspective Broadening": "asst_MDjAUuSTMgphokc3v5BZLKCT",
    "Combined": "asst_MDjAUuSTMgphokc3v5BZLKCT"  # You can update this ID as needed
}