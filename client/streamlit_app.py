import os
import requests
import streamlit as st

st.set_page_config(page_title="CMDB Client", layout="wide", page_icon="🧰")

st.title("🧰 CMDB Client – Home")

st.markdown(
    """
Hello!! Welcome to the CMDB client (By Nicky Khorasani).

This is the **home page**, where you can run a quick **Health Check** to confirm:

1. the FastAPI server is running
2. the NL->SQL model has finished loading

Use the sidebar to open the other pages. Here is a brief description of each page:
* **📥 Ingest** - Allows you to upload or generate sample data
* **📚 Browse** - Allows you to view Users, Devices, Apps, and CI items.
* **❓ Ask** - Allows you to ask natural-language questions view the generated SQL, and see the results of the query.
"""
)

api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
# st.text_input("API Base URL", value=api_url, disabled=True)

st.subheader("Health Check")
if st.button("Run health check"):
    try:
        r = requests.get(f"{api_url}/healthz", timeout=5)
        data = r.json()
        st.success("Server is reachable ✅")
        st.json(data)
        if not data.get("model_ready", False):
            st.warning("Model is not ready yet. Wait a moment or check logs.")
    except Exception as e:
        st.error(f"Health check failed: {e}")
