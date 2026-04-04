import streamlit as st
from app.ui.helpers import api


def render_tab_users(BASE: str) -> None:
    """List users and create new ones."""
    st.markdown("<div class='section-label'>Users</div>", unsafe_allow_html=True)

    # --- Create user form ---
    with st.expander("➕ Create new user", expanded=False):
        username = st.text_input("Username", key="new_user_username")
        email = st.text_input("Email", key="new_user_email")
        if st.button("Create user", key="create_user_btn"):
            if not username or not email:
                st.markdown("<div class='alert-err'>Username and email are required.</div>", unsafe_allow_html=True)
            else:
                status, data = api(
                    "POST", "/users", BASE,
                    json={"username": username, "email": email},
                )
                if status == 201:
                    st.markdown("<div class='alert-ok'>✓ User created.</div>", unsafe_allow_html=True)
                    st.rerun()
                else:
                    err = data.get("error", f"HTTP {status}") if isinstance(data, dict) else f"HTTP {status}"
                    st.markdown(f"<div class='alert-err'>✗ {err}</div>", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # --- Users list ---
    status, data = api("GET", "/users", BASE)

    if status is None or not isinstance(data, list):
        err = data.get("error", f"HTTP {status}") if isinstance(data, dict) else f"HTTP {status}"
        st.markdown(f"<div class='alert-err'>⚠ {err}</div>", unsafe_allow_html=True)
        return

    if not data:
        st.markdown("<div class='alert-warn'>No users found.</div>", unsafe_allow_html=True)
        return

    for user in data:
        uid = user.get("id", "?")
        uname = user.get("username", "")
        uemail = user.get("email", "")
        st.markdown(
            f"<div class='url-row'>"
            f"<span class='code-badge'>#{uid}</span>"
            f"<span class='orig-url'>@{uname}</span>"
            f"<span class='url-title-cell'>{uemail}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
