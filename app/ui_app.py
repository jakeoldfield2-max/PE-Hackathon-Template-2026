import streamlit as st
from app.ui.styles import apply_styles
from app.ui.sidebar import render_sidebar
from app.ui.dashboard import render_header_stats
from app.ui.tabs import render_all_tabs
from app.ui.helpers import api

st.set_page_config(
    page_title="URLPulse",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

apply_styles()

BASE = render_sidebar()

render_header_stats(BASE)

_, u_resp = api("GET", "/users", BASE)
users_list = u_resp if isinstance(u_resp, list) else []
user_map = {f"@{u['username']}  (id:{u['id']})": u["id"] for u in users_list}

render_all_tabs(BASE, user_map)
