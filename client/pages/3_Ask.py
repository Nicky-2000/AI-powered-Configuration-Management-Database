# client/pages/2_❓_Ask.py (example Ask page)
import streamlit as st
import pandas as pd
import api as API  # your client/api.py

st.title("❓ Ask (AI → SQL)")

q = st.text_input("Question", placeholder="Which users have 'Adam' in their name?")
limit = st.number_input("Limit", 1, 200, 100)

if st.button("Run"):
    try:
        res = API.ask(q=q, limit=int(limit))   # expects {"ok", "sql", "rows": [...]}
        st.subheader("Generated SQL")
        st.code(res["sql"], language="sql")
        rows = res.get("rows") or []

        # If single-row/single-column → render as a metric
        if len(rows) == 1 and isinstance(rows[0], dict) and len(rows[0]) == 1:
            k, v = next(iter(rows[0].items()))
            # normalize key like COUNT(*) → count
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
