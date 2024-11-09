import streamlit as st
from exa_py import Exa
from openai import OpenAI

def get_exa_client():
    """Get or create Exa client instance"""
    api_key = st.session_state.get("exa_api_key") or st.secrets["exa"]["api_key"]
    return Exa(api_key)

def get_openai_client():
    """Get or create OpenAI client instance"""
    return OpenAI(api_key=st.secrets["openai"]["api_key"])
