# client/components.py
import streamlit as st
import pandas as pd

def show_table(rows, caption: str | None = None):
    """Render a list[dict] as a dataframe; otherwise show JSON."""
    if caption:
        st.caption(caption)
    if isinstance(rows, list):
        if rows and isinstance(rows[0], dict):
            st.dataframe(pd.DataFrame(rows))
        else:
            st.write(rows)
    else:
        st.write(rows)

def show_json(obj, caption: str | None = None):
    if caption:
        st.caption(caption)
    st.json(obj)

def divider(label: str = ""):
    st.markdown(f"---\n**{label}**" if label else "---")
