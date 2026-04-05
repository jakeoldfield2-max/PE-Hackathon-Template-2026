import streamlit as st
from app.ui.helpers import api

def _load_urls(BASE):
    _, rv = api("GET", "/urls", BASE)
    if isinstance(rv, list):
        return rv
    if isinstance(rv, dict) and "urls" in rv:
        return rv.get("urls", [])
    return []


def _url_options(urls):
    options = []
    for item in urls:
        title = item.get("title") or "untitled"
        short_code = item.get("short_code") or "no-code"
        options.append(f"#{item.get('id')} • {short_code} • {title}")
    return options


def render_tab_manage(BASE):
    st.markdown('<div class="section-label">— update url</div>', unsafe_allow_html=True)
    st.caption("Calls PUT /urls/<id> — select the record from the live URL list")

    urls = _load_urls(BASE)
    if not urls:
        st.markdown('<div class="alert-warn">No URLs available. Create one in the shorten tab first.</div>', unsafe_allow_html=True)
        return

    options = _url_options(urls)
    selected_label = st.selectbox("URL", options, key="upd_url_select")
    selected_index = options.index(selected_label)
    selected_url = urls[selected_index]

    m1, m2 = st.columns([2, 1])
    with m1:
        upd_new_url = st.text_input(
            "NEW DESTINATION URL",
            value=selected_url.get("original_url", ""),
            key=f"upd_url_{selected_url['id']}",
        )
    with m2:
        upd_title = st.text_input(
            "NEW TITLE",
            value=selected_url.get("title", ""),
            key=f"upd_title_{selected_url['id']}",
        )
        upd_active = st.selectbox(
            "ACTIVE STATUS",
            ["true", "false"],
            index=0 if selected_url.get("is_active", True) else 1,
            key=f"upd_active_{selected_url['id']}",
        )

    if st.button("update →", key="upd_btn"):
        payload_u = {"is_active": upd_active == "true"}
        if upd_new_url.strip():
            payload_u["original_url"] = upd_new_url.strip()
        if upd_title.strip():
            payload_u["title"] = upd_title.strip()
        with st.spinner("updating…"):
            sc, rv = api("PUT", f"/urls/{selected_url['id']}", BASE, json=payload_u)
        if sc == 200:
            st.markdown(f'<div class="alert-ok">updated → #{selected_url["id"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-err">{rv.get("error","update failed")}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">— delete url</div>', unsafe_allow_html=True)
    st.caption("Calls DELETE /urls/<id> — permanent, cannot be undone")

    del_label = st.selectbox("URL TO DELETE", options, key="del_url_select")
    del_index = options.index(del_label)
    del_url = urls[del_index]
    dc1, dc2 = st.columns([1, 3])
    with dc1:
        del_btn = st.button("delete →", key="del_btn")
    with dc2:
        confirm = st.checkbox("I understand this cannot be undone", key="confirm_del")

    if del_btn:
        if not confirm:
            st.markdown('<div class="alert-warn">tick the confirmation box first</div>', unsafe_allow_html=True)
        else:
            with st.spinner("deleting…"):
                sc, rv = api("DELETE", f"/urls/{del_url['id']}", BASE)
            if sc in (200, 204):
                st.markdown(f'<div class="alert-ok">deleted → #{del_url["id"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-err">{rv.get("error","delete failed")}</div>', unsafe_allow_html=True)
