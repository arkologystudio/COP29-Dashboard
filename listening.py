import streamlit as st
from listening import get_responding_data  # Import the function

# Initialize the list in session state if it doesn't exist
if "listening_data" not in st.session_state:
    st.session_state.listening_data = [
        "#globalwarming", 
        "#cop25", 
        "@longnose11", 
        "@hightail312"
    ]

# Fetch the responding data from the listening API
responding_data = get_responding_data()  # This will fetch live data

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

# Responding
with tab2:
    st.header("Responding")
    st.write("List of identified harmful narratives:")
    
    for narrative in responding_data:
        st.subheader(narrative["title"])
        st.write(f"Link: [Click here]({narrative['link']})")
        st.write(f"Content: {narrative['content']}")
        st.write("---")
