import streamlit as st
from datetime import datetime
from app.ui.helpers import api

def render_tab_users(BASE):
    st.markdown('<div class="section-label">— create user</div>', unsafe_allow_html=True)

    uc1, uc2, uc3 = st.columns([2, 2, 1])
    with uc1:
        new_uname = st.text_input("USERNAME", placeholder="alice", key="new_uname")
    with uc2:
        new_email = st.text_input("EMAIL", placeholder="alice@example.com", key="new_email")
    with uc3:
        st.markdown("<br>", unsafe_allow_html=True)
        create_user = st.button("create →", use_container_width=True, key="create_user_btn")

    if create_user:
        if not new_uname or not new_email:
            st.markdown('<div class="alert-err">username and email are both required</div>', unsafe_allow_html=True)
        else:
            with st.spinner("creating…"):
                sc, rv = api("POST", "/users", BASE, json={"username": new_uname, "email": new_email})
            if sc in (200, 201):
                st.markdown(f'<div class="alert-ok">created — @{new_uname}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-err">{rv.get("error","failed")}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label" style="margin-top:1.5rem;">— all users</div>', unsafe_allow_html=True)
    if st.button("↺ refresh users", key="refresh_users"):
        st.rerun()

    _, ur = api("GET", "/users", BASE)
    all_users = ur if isinstance(ur, list) else []

    if not all_users:
        st.markdown('<div class="alert-warn">No users yet — run POST /seed or create one above</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="display:flex;gap:1rem;padding:0 1rem 0.3rem;">'
            '<span style="font-family:JetBrains Mono,monospace;font-size:0.6rem;color:#2a2a32;letter-spacing:0.12em;min-width:30px;">ID</span>'
            '<span style="font-family:JetBrains Mono,monospace;font-size:0.6rem;color:#2a2a32;letter-spacing:0.12em;flex:1;">USERNAME</span>'
            '<span style="font-family:JetBrains Mono,monospace;font-size:0.6rem;color:#2a2a32;letter-spacing:0.12em;flex:2;">EMAIL</span>'
            '<span style="font-family:JetBrains Mono,monospace;font-size:0.6rem;color:#2a2a32;letter-spacing:0.12em;min-width:130px;text-align:right;">CREATED</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        for u in all_users:
            uid   = u.get("id","")
            uname = u.get("username","")
            email = u.get("email","")
            cat   = u.get("created_at","")
            if cat:
                try: cat = datetime.fromisoformat(cat.replace("Z","")).strftime("%d %b %Y %H:%M")
                except Exception: pass
            st.markdown(
                f'<div class="url-row">'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.78rem;color:#3d3d45;min-width:30px;">#{uid}</span>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;color:#4ade80;flex:1;">@{uname}</span>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.78rem;color:#6b6b74;flex:2;">{email}</span>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.7rem;color:#2e2e38;min-width:130px;text-align:right;">{cat}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
