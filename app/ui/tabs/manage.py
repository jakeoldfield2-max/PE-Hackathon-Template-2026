import streamlit as st
import json
from ui.helpers import api

def render_tab_manage(BASE):
    st.markdown('<div class="section-label">— update url</div>', unsafe_allow_html=True)
    st.caption("Calls POST /update — identify the record by short_code")

    m1, m2 = st.columns([2, 1])
    with m1:
        upd_code    = st.text_input("SHORT CODE", placeholder="abc123", key="upd_code")
        upd_new_url = st.text_input("NEW DESTINATION URL", placeholder="https://new-destination.com", key="upd_url")
    with m2:
        upd_title  = st.text_input("NEW TITLE", placeholder="Updated title", key="upd_title")
        upd_active = st.selectbox("ACTIVE STATUS", ["true", "false"], key="upd_active")

    if st.button("update →", key="upd_btn"):
        if not upd_code:
            st.markdown('<div class="alert-err">short code is required</div>', unsafe_allow_html=True)
        else:
            payload_u = {"short_code": upd_code, "is_active": upd_active == "true"}
            if upd_new_url.strip(): payload_u["original_url"] = upd_new_url.strip()
            if upd_title.strip():   payload_u["title"] = upd_title.strip()
            with st.spinner("updating…"):
                sc, rv = api("POST", "/update", BASE, json=payload_u)
            if sc in (200, 201):
                st.markdown(f'<div class="alert-ok">updated → {upd_code}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-err">{rv.get("error","update failed")}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">— delete url</div>', unsafe_allow_html=True)
    st.caption("Calls POST /delete — permanent, cannot be undone")

    del_code = st.text_input("SHORT CODE TO DELETE", placeholder="abc123", key="del_code")
    dc1, dc2 = st.columns([1, 3])
    with dc1:
        del_btn = st.button("delete →", key="del_btn")
    with dc2:
        confirm = st.checkbox("I understand this cannot be undone", key="confirm_del")

    if del_btn:
        if not del_code:
            st.markdown('<div class="alert-err">short code is required</div>', unsafe_allow_html=True)
        elif not confirm:
            st.markdown('<div class="alert-warn">tick the confirmation box first</div>', unsafe_allow_html=True)
        else:
            with st.spinner("deleting…"):
                sc, rv = api("POST", "/delete", BASE, json={"short_code": del_code})
            if sc in (200, 201, 204):
                st.markdown(f'<div class="alert-ok">deleted → {del_code}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-err">{rv.get("error","delete failed")}</div>', unsafe_allow_html=True)
