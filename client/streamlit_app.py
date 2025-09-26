# client/streamlit_app.py
import os
import requests
import streamlit as st

st.set_page_config(page_title="CMDB Client", layout="wide")
st.title("🧰 CMDB Client")

st.markdown("""
This is the home page.

Use the **sidebar Pages** to open:
- **📥 Ingest** — Generate synthetic hardware/Okta data or paste raw JSON and POST to `/ingest`. Shows batch success/failure and sample errors.
- **📚 Browse** — Call `/devices`, `/users`, `/apps` with filters and see results in tables.
- **❓ Ask** — Ask natural language questions. Backend converts to SQL (with guardrails) and returns rows. Also shows the generated SQL.
""")

with st.sidebar:
    st.header("Settings")
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    st.text_input("API Base URL (from env)", value=api_url, disabled=True)
    if st.button("Health check"):
        try:
            r = requests.get(f"{api_url}/healthz", timeout=5)
            st.success(r.json())
        except Exception as e:
            st.error(f"Health check failed: {e}")

st.info("Tip: set `API_BASE_URL` in `client/.env` (copy from `.env.sample`) or export it before running `./run_client.sh`.")
