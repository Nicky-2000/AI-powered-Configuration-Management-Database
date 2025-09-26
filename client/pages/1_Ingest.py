import streamlit as st, random, requests, json, time, io
import api as API
from gen_data import gen_hardware_record, gen_okta_user_record
from components import show_json
from datetime import datetime, timedelta

st.title("📥 Ingest")

# ------------------------
# Session state
# ------------------------
if "generated_records" not in st.session_state:
    st.session_state.generated_records = []
if "failed_items" not in st.session_state:
    st.session_state.failed_items = []

# ------------------------
# Controls
# ------------------------
col1, col2, col3 = st.columns(3)
with col1:
    kind = st.selectbox("Kind", ["hardware", "okta", "mixed"], key="ing_kind")
with col2:
    total_n = st.number_input("Total records", 1, 10000, 200, key="ing_total")
with col3:
    batch_size = st.number_input("Batch size", 1, 1000, 50, key="ing_batch")

with st.expander("Advanced options"):
    c1, c2, c3 = st.columns(3)
    with c1:
        seed = st.number_input("Random seed", 0, 999999, 0, key="ing_seed")
    with c2:
        rate = st.number_input("Throttle (records/sec)", 0.0, 1000.0, 0.0, 0.1, key="ing_rate")
    with c3:
        if kind == "mixed":
            mix_ratio = st.slider("Mixed ratio (hardware%)", 0, 100, 50, key="ing_ratio")
        else:
            mix_ratio = 50

# ------------------------
# Helpers
# ------------------------
def _chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i+size]

def _gen(kind: str, n: int, mix_ratio: int = 50):
    if seed:
        random.seed(int(seed))
    if kind == "hardware":
        return [gen_hardware_record() for _ in range(n)]
    if kind == "okta":
        return [gen_okta_user_record() for _ in range(n)]
    # mixed
    h = int(round(n * (mix_ratio / 100.0)))
    o = n - h
    recs = [gen_hardware_record() for _ in range(h)] + [gen_okta_user_record() for _ in range(o)]
    random.shuffle(recs)
    return recs

def _dl_button_from_records(records, label="⬇️ Download generated JSON", file_name="generated.json"):
    buf = io.StringIO()
    json.dump(records, buf, indent=2)
    st.download_button(label, data=buf.getvalue(), file_name=file_name, mime="application/json")

# ------------------------
# Generate & Preview
# ------------------------
cA, cB, cC = st.columns(3)
with cA:
    if st.button("🎲 Generate dataset", key="btn_gen"):
        st.session_state.generated_records = _gen(kind, total_n, mix_ratio)
        st.success(f"Generated {len(st.session_state.generated_records)} {kind} record(s).")
with cB:
    if st.button("Preview first 2 elements", key="btn_preview"):
        if not st.session_state.generated_records:
            st.info("No generated dataset yet — click **Generate dataset** first.")
        else:
            show_json(st.session_state.generated_records[:2], caption="Preview (first 2 records)")
with cC:
    if st.session_state.generated_records:
        _dl_button_from_records(st.session_state.generated_records)

st.divider()

# ------------------------
# Ingest generated dataset
# ------------------------
if st.session_state.generated_records:
    prog = st.progress(0.0)
    eta_text = st.empty()

    if st.button("➡️ Ingest generated dataset", key="btn_ingest_gen"):
        recs = st.session_state.generated_records
        total = len(recs)
        ok_batches = fail_batches = ok_records = fail_records = 0
        st.session_state.failed_items = []

        # Optional rate -> sleep per batch
        batch_sleep = 0.0
        if rate and rate > 0:
            batch_sleep = batch_size / float(rate)

        start = time.time()
        for i, chunk in enumerate(_chunked(recs, batch_size), start=1):
            try:
                resp = API.ingest(chunk)
                ok = int(resp.get("ingested", 0))
                failed = int(resp.get("failed", 0) or max(0, len(chunk) - ok))
                ok_records += ok
                fail_records += failed
                if failed:
                    fail_batches += 1
                    if resp.get("errors"):
                        # attach the raw chunk for potential retry visibility
                        st.session_state.failed_items.extend(resp["errors"])
                else:
                    ok_batches += 1
                st.write(f"[{i}] → {resp}")
            except requests.HTTPError as e:
                fail_batches += 1
                fail_records += len(chunk)
                msg = e.response.text[:400] if e.response is not None else str(e)
                st.error(f"[{i}] HTTP error: {msg}")
                # log each record as failed
                st.session_state.failed_items.extend([{"error": msg, "record": r} for r in chunk])
            except Exception as e:
                fail_batches += 1
                fail_records += len(chunk)
                st.error(f"[{i}] {e}")
                st.session_state.failed_items.extend([{"error": str(e), "record": r} for r in chunk])

            # progress + ETA
            prog.progress(i / ((total + batch_size - 1) // batch_size))
            elapsed = time.time() - start
            done = min(i * batch_size, total)
            rate_now = (done / elapsed) if elapsed > 0 else 0.0
            remaining = max(total - done, 0)
            eta = (remaining / rate_now) if rate_now > 0 else 0
            eta_text.caption(f"Progress: {done}/{total} (~{rate_now:.1f} rec/s) | ETA ~ {eta:.1f}s")

            if batch_sleep:
                time.sleep(batch_sleep)

        st.success("Done.")
        st.write(f"**Batches**: success={ok_batches} failed={fail_batches} total={ok_batches+fail_batches}")
        st.write(f"**Records**: success={ok_records} failed={fail_records} total={total}")
        if st.session_state.failed_items:
            st.warning(f"{len(st.session_state.failed_items)} failed item(s). See details below.")
            show_json(st.session_state.failed_items[:10])

st.divider()

# ------------------------
# Retry failed items
# ------------------------
if st.session_state.failed_items:
    if st.button("🔁 Retry failed now", key="btn_retry_failed"):
        # extract raw records if available; otherwise build minimal error-only payload
        retry_payload = []
        for e in st.session_state.failed_items:
            rec = e.get("record")
            if isinstance(rec, dict):
                retry_payload.append(rec)
        if not retry_payload:
            st.info("No raw records captured in failures to retry.")
        else:
            try:
                resp = API.ingest(retry_payload)
                st.success({"retry_result": resp, "retried_records": len(retry_payload)})
                # clear after retry to avoid duplicates
                st.session_state.failed_items = []
            except Exception as e:
                st.error(f"Retry failed: {e}")

st.divider()

# ------------------------
# Raw JSON paths (manual)
# ------------------------
st.caption("Or paste/upload raw JSON and POST directly to `/ingest`")

cU, cP = st.columns(2)
with cU:
    up = st.file_uploader("Upload JSON file (array)", type=["json"], key="ing_upload")
    if up and st.button("POST uploaded JSON", key="btn_upload_post"):
        try:
            data = json.load(up)
            resp = API.ingest(data)
            st.success(resp)
        except Exception as e:
            st.error(e)

with cP:
    payload_text = st.text_area("Paste JSON array", height=180, key="ing_textarea",
                                placeholder='[{"device_id":"C-123","hostname":"host-1", ...}]')
    if st.button("POST pasted JSON", key="btn_paste_post"):
        try:
            data = json.loads(payload_text)
            resp = API.ingest(data)
            st.success(resp)
        except Exception as e:
            st.error(e)
