# client/pages/3_📚_Browse.py
import streamlit as st
import pandas as pd
import api as API
from components import show_table

st.title("📚 Browse")

tab1, tab2, tab3, tab4 = st.tabs(["Devices", "Users", "Apps", "Lookup CI"])

with tab1:
    st.subheader("Devices")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status = st.text_input("status", placeholder="active", key="dev_status")
    with c2:
        location = st.text_input("location contains", placeholder="London", key="dev_location")
    with c3:
        limit = st.number_input("limit", 1, 2000, 100, key="dev_limit")
    with c4:
        offset = st.number_input("offset", 0, 100000, 0, key="dev_offset")
    if st.button("Fetch devices", key="btn_fetch_devices"):
        params = {"limit": int(limit), "offset": int(offset)}
        if status: params["status"] = status
        if location: params["location"] = location
        try:
            rows = API.devices(**params)
            show_table(rows)
        except Exception as e:
            st.error(e)

with tab2:
    st.subheader("Users")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_u = st.text_input("status", placeholder="active", key="user_status")
    with c2:
        mfa = st.selectbox("mfa_enabled", ["", "true", "false"], key="user_mfa")
    with c3:
        app = st.text_input("has app", placeholder="Slack", key="user_app")
    with c4:
        limit_u = st.number_input("limit", 1, 2000, 100, key="user_limit")
    if st.button("Fetch users", key="btn_fetch_users"):
        params = {"limit": int(limit_u)}
        if status_u: params["status"] = status_u
        if mfa: params["mfa"] = (mfa == "true")
        if app: params["app"] = app
        try:
            rows = API.users(**params)
            show_table(rows)
        except Exception as e:
            st.error(e)

with tab3:
    st.subheader("Apps")
    q = st.text_input("name contains", key="apps_q")
    limit_a = st.number_input("limit", 1, 2000, 100, key="apps_limit")
    if st.button("Fetch apps", key="btn_fetch_apps"):
        params = {"limit": int(limit_a)}
        if q: params["q"] = q
        try:
            rows = API.apps(**params)
            show_table(rows)
        except Exception as e:
            st.error(e)

with tab4:
    st.subheader("Lookup CI by ID")
    ci_id = st.text_input("Identifier", placeholder="e.g., dev-123, U001, Slack")
    kind = st.selectbox("Kind (optional)", ["", "device", "user", "app"])
    if st.button("Fetch CI", key="btn_fetch_ci"):
        try:
            res = API.ci(ci_id, kind if kind else None)
            st.json(res)
        except Exception as e:
            st.error(e)
