# client/pages/2_❓_Ask.py
import streamlit as st
import pandas as pd
import api as API

st.title("❓ Ask (AI → SQL)")

# --- Collapsible example queries ---
with st.expander("💡 Example questions to try (click to expand)"):
    st.markdown(
        """
        ```
        How many devices are in London?
        How many users have MFA disabled?
        Show all devices with encryption turned off.
        What are the top 5 operating systems among all devices?
        Which location has the most devices?
        Show the most recent last_login time for any user.
        How many devices are running Windows 11?
        List all retired devices located in New York HQ.
        Give me every user whose name contains the letter 'a'.
        How many devices are not encrypted and in Paris?
        ```
        """
    )

# --- Input + Run ---
q = st.text_input("Question", placeholder="Type or paste a question here…")
limit = st.number_input("Limit", 1, 200, 100)

if st.button("Run"):
    try:
        res = API.ask(q=q, limit=int(limit))
        st.subheader("Generated SQL")
        st.code(res["sql"], language="sql")
        rows = res.get("rows") or []

        if len(rows) == 1 and isinstance(rows[0], dict) and len(rows[0]) == 1:
            k, v = next(iter(rows[0].items()))
            key_norm = "count" if k.lower().strip() in ("count(*)", "count") else k
            st.subheader("Result")
            st.metric(label=key_norm, value=str(v))
        elif rows:
            st.subheader("Rows")
            st.dataframe(pd.DataFrame(rows))
        else:
            st.info("No rows returned.")
    except Exception as e:
        st.error(e)
