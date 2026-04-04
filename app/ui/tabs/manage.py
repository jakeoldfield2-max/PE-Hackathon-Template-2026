import streamlit as st
from app.ui.helpers import api


def render_tab_manage(BASE: str) -> None:
    """Update or delete existing URLs."""
    st.markdown("<div class='section-label'>Update a URL field</div>", unsafe_allow_html=True)

    with st.expander("✏️ Update field", expanded=True):
        url_id = st.number_input("URL ID", min_value=1, step=1, key="manage_url_id")
        user_id = st.number_input("Your user ID", min_value=1, step=1, key="manage_user_id")
        field = st.selectbox("Field to update", ["title", "is_active", "original_url"], key="manage_field")

        if field == "is_active":
            new_value = st.checkbox("New value (active?)", key="manage_new_bool")
        else:
            new_value = st.text_input("New value", key="manage_new_str")

        if st.button("Update", key="manage_update_btn"):
            status, data = api(
                "POST", "/update", BASE,
                json={
                    "user_id": int(user_id),
                    "url_id": int(url_id),
                    "field": field,
                    "new_value": new_value,
                },
            )
            if status == 200:
                st.markdown("<div class='alert-ok'>✓ URL updated successfully.</div>", unsafe_allow_html=True)
            else:
                err = data.get("error", f"HTTP {status}") if isinstance(data, dict) else f"HTTP {status}"
                st.markdown(f"<div class='alert-err'>✗ {err}</div>", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Delete a URL</div>", unsafe_allow_html=True)

    with st.expander("🗑️ Delete by title", expanded=False):
        del_user_id = st.number_input("Your user ID", min_value=1, step=1, key="del_user_id")
        del_title = st.text_input("Title of URL to delete", key="del_title")
        if st.button("Delete", key="delete_btn"):
            if not del_title:
                st.markdown("<div class='alert-err'>Title is required.</div>", unsafe_allow_html=True)
            else:
                status, data = api(
                    "POST", "/delete", BASE,
                    json={"user_id": int(del_user_id), "title": del_title},
                )
                if status == 200:
                    st.markdown("<div class='alert-ok'>✓ URL deleted.</div>", unsafe_allow_html=True)
                else:
                    err = data.get("error", f"HTTP {status}") if isinstance(data, dict) else f"HTTP {status}"
                    st.markdown(f"<div class='alert-err'>✗ {err}</div>", unsafe_allow_html=True)
