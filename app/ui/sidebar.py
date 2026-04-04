import streamlit as st


def render_sidebar() -> str:
    """Render the sidebar and return the selected API base URL."""
    with st.sidebar:
        st.markdown(
            "<div style='font-family:JetBrains Mono,monospace;font-size:0.65rem;"
            "color:#2e2e38;letter-spacing:0.14em;text-transform:uppercase;"
            "margin-bottom:0.4rem;'>service</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-family:JetBrains Mono,monospace;font-size:1.1rem;"
            "font-weight:700;color:#4ade80;margin:0 0 1.4rem 0;'>URLPulse ⚡</p>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div class='section-label'>API Base URL</div>",
            unsafe_allow_html=True,
        )
        base = st.text_input(
            "base_url",
            value="http://localhost:5000",
            label_visibility="collapsed",
            key="sidebar_base_url",
        )

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        st.markdown(
            "<div class='section-label'>Connection</div>",
            unsafe_allow_html=True,
        )

        from app.ui.helpers import probe

        alive, _ = probe(base, "/health")
        ready, _ = probe(base, "/ready")

        if alive:
            st.markdown(
                "<span class='health-ok'>"
                "<span class='health-dot-ok'></span>health&nbsp;ok</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<span class='health-err'>"
                "<span class='health-dot-err'></span>health&nbsp;down</span>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:0.4rem;'></div>", unsafe_allow_html=True)

        if ready:
            st.markdown(
                "<span class='health-ok'>"
                "<span class='health-dot-ok'></span>ready&nbsp;ok</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<span class='health-err'>"
                "<span class='health-dot-err'></span>not&nbsp;ready</span>",
                unsafe_allow_html=True,
            )

    return base
