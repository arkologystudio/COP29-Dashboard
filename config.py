import streamlit as st

SEARCH_CARD_TEMPLATE_FILE = "templates/search_result_card.html"

# Response strategies
RESPONSE_STRATEGIES = {
    "Truth Query": st.secrets["openai"]["truth_query_assistant_id"],
    "Perspective Broadening": st.secrets["openai"]["perspective_assistant_id"],
    "Combined": st.secrets["openai"]["combined_assistant_id"]
}

VOICES = { "Default": "DEFAULT", "Sylva": st.secrets["openai"]["sylva_assistant_id"], "Khataza": st.secrets["openai"]["khataza_assistant_id"]}