import streamlit as st
from datetime import datetime
from app.ui.helpers import api, probe
from app.ui.styles import get_theme, toggle_theme

def render_sidebar():
    with st.sidebar:
        theme = get_theme()
        is_dark = theme == "dark"

        # ── brand header ──────────────────────────────────────────────────
        st.markdown(
            '<div style="font-family:JetBrains Mono,monospace;font-size:1.2rem;font-weight:700;'
            'color:var(--accent);margin-bottom:0.1rem;">URLPulse</div>'
            '<div style="font-family:JetBrains Mono,monospace;font-size:0.62rem;'
            'color:var(--text-xxdim);letter-spacing:0.1em;margin-bottom:1.5rem;">'
            'MLH PE HACKATHON 2026</div>',
            unsafe_allow_html=True,
        )

        # ── theme toggle ──────────────────────────────────────────────────
        st.markdown('<div class="section-label">— appearance</div>', unsafe_allow_html=True)
        toggle_label = "☀️  switch to light" if is_dark else "🌙  switch to dark"
        if st.button(toggle_label, use_container_width=True, key="theme_toggle_btn"):
            toggle_theme()
            st.rerun()

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── backend selector ──────────────────────────────────────────────
        st.markdown('<div class="section-label">— backend</div>', unsafe_allow_html=True)
        mode = st.radio("mode", ["Docker  :80", "Local  :5000"], label_visibility="collapsed")
        BASE = "http://localhost" if "Docker" in mode else "http://localhost:5000"
        custom = st.text_input("CUSTOM BASE URL", value="", placeholder="https://34.x.x.x")
        if custom.strip():
            BASE = custom.strip().rstrip("/")
        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.7rem;'
            f'color:var(--text-xdim);margin-bottom:1rem;">{BASE}</div>',
            unsafe_allow_html=True,
        )

        # ── health status ─────────────────────────────────────────────────
        st.markdown('<div class="section-label">— status</div>', unsafe_allow_html=True)
        ok_health, _ = probe(BASE, "/health")
        ok_ready, _  = probe(BASE, "/ready")

        if ok_health and ok_ready:
            cls, dot, lbl = "health-ok",  "health-dot-ok",  "System Online"
        elif ok_health and not ok_ready:
            cls, dot, lbl = "alert-warn", "health-dot-err", "Degraded (No DB)"
        else:
            cls, dot, lbl = "health-err", "health-dot-err", "System Offline"

        st.markdown(
            f'<div class="{cls}"><span class="{dot}"></span>{lbl}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↺ refresh checks", use_container_width=True, key="refresh_health"):
            st.rerun()

        # ── seed demo data ────────────────────────────────────────────────
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">— seed demo data</div>', unsafe_allow_html=True)
        st.caption("Clears all data and inserts 3 users · 10 URLs · 10 events")
        if st.button("POST /seed", use_container_width=True, key="seed_btn"):
            s, r = api("POST", "/seed", BASE)
            if s in (200, 201):
                st.markdown(
                    f'<div class="alert-ok">seeded — {r.get("users_created",0)}u '
                    f'· {r.get("urls_created",0)}url · {r.get("events_created",0)}evt</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="alert-err">{r.get("error","seed failed")}</div>',
                    unsafe_allow_html=True,
                )

        # ── timestamp ─────────────────────────────────────────────────────
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.6rem;'
            f'color:var(--text-xxxdim);">{datetime.now().strftime("%H:%M:%S")}</div>',
            unsafe_allow_html=True,
        )

    return BASE
