import streamlit as st
import os
import subprocess
import sys
from chromadb import PersistentClient

DOCS_DIR = "./docs"
CHROMA_DB_DIR = "./chroma_db"

st.set_page_config(page_title="Document Manager", layout="centered")

st.title("📄 Document Management Dashboard")

with st.expander("📤 Upload Document"):
    uploaded_file = st.file_uploader("Choose a PDF or TXT file", type=["pdf", "txt"])
    if uploaded_file is not None:
        file_path = os.path.join(DOCS_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"{uploaded_file.name} uploaded successfully!")

with st.expander("📁 View and Manage Documents"):
    docs = os.listdir(DOCS_DIR)
    if docs:
        selected_docs = st.multiselect("Select documents to delete:", docs)
        if st.button("🗑️ Delete Selected Documents"):
            for doc in selected_docs:
                os.remove(os.path.join(DOCS_DIR, doc))
            st.success("Selected documents deleted successfully!")
    else:
        st.info("No documents found in the docs directory.")

with st.expander("🔁 Re-index and Monitor"):
    if st.button("Re-index Documents", use_container_width=True):
        result = subprocess.run(
            [sys.executable, "populate_db.py"], capture_output=True, text=True
        )
        if result.returncode == 0:
            st.success("✅ Documents re-indexed successfully!")
            try:
                client = PersistentClient(path=CHROMA_DB_DIR)
                collection = client.get_collection("langchain")
                count = collection.count()
                st.metric(label="📦 Total Chunks Indexed", value=count)
            except Exception as e:
                st.warning("Unable to fetch chunk count after reindex.")
                st.text(str(e))
            finally:
                try:
                    client._client.reset()  # Explicitly shut down
                except Exception:
                    pass
                del client
        else:
            st.error("❌ Re-indexing failed. Check logs below.")
            st.code(result.stderr)
