import streamlit as st
from ui.tabs.shorten import render_tab_shorten
from ui.tabs.urls import render_tab_urls
from ui.tabs.users import render_tab_users
from ui.tabs.manage import render_tab_manage

def render_all_tabs(BASE, user_map):
    tab_shorten, tab_urls, tab_users, tab_manage = st.tabs([
        "  ⚡ shorten  ", "  📋 all urls  ", "  👤 users  ", "  ✏️ manage  "
    ])

    with tab_shorten:
        render_tab_shorten(BASE, user_map)
    with tab_urls:
        render_tab_urls(BASE)
    with tab_users:
        render_tab_users(BASE)
    with tab_manage:
        render_tab_manage(BASE)
