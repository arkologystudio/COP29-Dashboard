import streamlit as st
import os
from listening import get_responding_data 

LISTENING_TAGS_FILE = "listening_tags.txt"
LISTENING_RESPONSES_FILE = "listening_responses.txt"


def load_listening_tags():
    if os.path.exists(LISTENING_TAGS_FILE):
        with open(LISTENING_TAGS_FILE, "r") as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    return []

def save_listening_tags(tags_list):
    with open(LISTENING_TAGS_FILE, "w") as file:
        for tag in tags_list:
            file.write(f"{tag}\n")

def load_listening_responses():
    if os.path.exists(LISTENING_RESPONSES_FILE):
        with open(LISTENING_RESPONSES_FILE, "r", encoding="utf-8") as file:
            responses = []
            for line in file.readlines():
                title, link, content = line.strip().split(" || ")
                responses.append({
                    "title": title,
                    "link": link,
                    "content": content
                })
            return responses
    return []


def save_listening_responses(responses_list):
    with open(LISTENING_RESPONSES_FILE, "w", encoding="utf-8") as file:
        for response in responses_list:
            file.write(f"{response['title']} || {response['link']} || {response['content']}\n")


if "listening_data" not in st.session_state:
    st.session_state.listening_data = load_listening_tags()

responding_data = load_listening_responses()

st.title("Dashboard")

tab1, tab2 = st.tabs(["Listening", "Responding"])

# Listening
with tab1:
    st.header("Listening")

    listening_data_str = "\n".join(st.session_state.listening_data)
    
    user_input = st.text_area("Listening for:", listening_data_str)
    
    if st.button("Update List"):
        st.session_state.listening_data = user_input.split("\n")
        save_listening_tags(st.session_state.listening_data)
        st.success("List updated successfully!")


    if st.button("Find Narratives"):
        new_responses = get_responding_data(query=", ".join(st.session_state.listening_data))
        responding_data.extend(new_responses)
        save_listening_responses(responding_data)
        st.success("Narratives fetched and saved successfully!")

# Responding
with tab2:
    st.header("Responding")
    st.write("List of identified harmful narratives:")
    
    if responding_data:
        for narrative in responding_data:
            st.subheader(narrative["title"])
            st.write(f"Link: [Click here]({narrative['link']})")
            st.write(f"Content: {narrative['content']}")
            st.write("---")
    else:
        st.write("No harmful narratives found yet. Please use the 'Find Narratives' button to search.")
