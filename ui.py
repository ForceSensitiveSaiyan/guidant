import os
import streamlit as st
import requests

API_URL = os.getenv("API_URL", "http://api:8000")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "600"))  # seconds

st.set_page_config(page_title="Guidant", layout="centered")

# Set custom background color
st.markdown(
    """
    <style>
        body {
            background-color: #a80000;
        }
        .stApp {
            background-color: #a80000;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Show logo
st.image("./assets/logo.svg", width=70)

# App title
st.title("Guidant")

# Input form
with st.form("ask_form", clear_on_submit=False):
    question = st.text_input("Ask a question:", key="question_input")
    submitted = st.form_submit_button("Ask")

    if submitted and question:
        response = requests.post(f"{API_URL}/ask", json={"question": question}, timeout=(10, REQUEST_TIMEOUT))
        if response.ok:
            answer = response.json()["answer"]
            st.markdown("### Answer:")
            st.markdown(answer)
        else:
            st.error("API request failed.")
