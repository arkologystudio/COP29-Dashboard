import streamlit as st
from fetch_data import get_responding_data  # Import from fetch_data.py now

if "listening_data" not in st.session_state:
    st.session_state.listening_data = [
        "#globalwarming", 
        "#cop25", 
        "@longnose11", 
        "@hightail312"
    ]

if "responding_data" not in st.session_state:
    st.session_state.responding_data = []

st.title("Dashboard")

tab1, tab2 = st.tabs(["Listening", "Responding"])

# Listening
with tab1:
    st.header("Listening")
    
    listening_data_str = "\n".join(st.session_state.listening_data)
    
    user_input = st.text_area("Listening for:", listening_data_str)
    
    if st.button("Update List"):
        st.session_state.listening_data = user_input.split("\n")
        st.success("List updated successfully!")
    
    if st.button("Find Narratives"):
        st.session_state.responding_data = get_responding_data()
        st.success("Narratives fetched successfully!")

# Responding
with tab2:
    st.header("Responding")
    st.write("List of identified harmful narratives:")
    
    if st.session_state.responding_data:
        for narrative in st.session_state.responding_data:
            st.subheader(narrative["title"])
            st.write(f"Link: [Click here]({narrative['link']})")
            st.write(f"Content: {narrative['content']}")
            st.write("---")
    else:
        st.write("No harmful narratives found yet. Please use the 'Find Narratives' button to search.")
