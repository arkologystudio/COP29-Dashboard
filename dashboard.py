import streamlit as st
import os
import json
from listening import get_responding_data

LISTENING_TAGS_FILE = "listening_tags.json"
LISTENING_RESPONSES_FILE = "listening_responses.json"
CARD_TEMPLATE_FILE = "templates/response_card.html"

def load_listening_tags():
    if os.path.exists(LISTENING_TAGS_FILE):
        try:
            with open(LISTENING_TAGS_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            st.error(f"Error: {LISTENING_TAGS_FILE} contains invalid JSON. Resetting to an empty list.")
            return []
    return []

def save_listening_tags(tags_list):
    with open(LISTENING_TAGS_FILE, "w", encoding="utf-8") as file:
        json.dump(tags_list, file, indent=4)

def load_listening_responses():
    if os.path.exists(LISTENING_RESPONSES_FILE):
        try:
            with open(LISTENING_RESPONSES_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            st.error(f"Error: {LISTENING_RESPONSES_FILE} contains invalid JSON. Resetting to an empty list.")
            return []
    return []

def save_listening_responses(responses_list):
    with open(LISTENING_RESPONSES_FILE, "w", encoding="utf-8") as file:
        json.dump(responses_list, file, indent=4)

def remove_response(title):
    responses = load_listening_responses()
    updated_responses = [r for r in responses if r["title"] != title]
    save_listening_responses(updated_responses)
    return updated_responses

def load_card_template():
    with open(CARD_TEMPLATE_FILE, "r", encoding="utf-8") as file:
        return file.read()

if "listening_data" not in st.session_state:
    st.session_state.listening_data = load_listening_tags()

if "responding_data" not in st.session_state:
    st.session_state.responding_data = load_listening_responses()

st.title("Dashboard")

tab1, tab2 = st.tabs(["Responding", "Listening"])

# Responding
with tab1:
    st.header("Responding")
    st.write("List of identified harmful narratives:")

    if st.button("Find Narratives"):
        responding_data = get_responding_data()
        st.session_state.responding_data = responding_data
        st.success("Narratives fetched successfully!")

    if st.session_state.responding_data:
        card_template = load_card_template()
        for narrative in st.session_state.responding_data:
            card_html = card_template.replace("{{ title }}", narrative['title']) \
                                     .replace("{{ narrative }}", narrative['narrative']) \
                                     .replace("{{ link }}", narrative['link']) \
                                     .replace("{{ content }}", narrative['content'])

            st.markdown(card_html, unsafe_allow_html=True)

            # Mark completed button
            if st.button("Mark Completed", key=f"key_{narrative['title']}", on_click=remove_response, args=(narrative['title'],)):
                st.session_state.dummy_flag = not st.session_state.get('dummy_flag', False)
    else:
        st.write("No harmful narratives found yet. Please use the 'Find Narratives' button to search.")

# Listening
with tab2:
    st.header("Listening")

    listening_data_str = "\n".join(st.session_state.listening_data)
    
    user_input = st.text_area("Listening for:", listening_data_str)
    
    if st.button("Update List"):
        st.session_state.listening_data = user_input.split("\n")
        save_listening_tags(st.session_state.listening_data)
        st.success("List updated successfully!")
