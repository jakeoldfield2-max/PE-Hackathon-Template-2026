import streamlit as st
from app.ui.helpers import api

def render_tab_urls(BASE):
    st.markdown('<div class="section-label">— all short links</div>', unsafe_allow_html=True)

    fc, sc2, rc = st.columns([3, 2, 1])
    with fc:
        search  = st.text_input("FILTER", placeholder="code / url / title…", key="url_search")
    with sc2:
        sort_by = st.selectbox("SORT", ["newest first", "oldest first", "code a→z", "active first"], key="url_sort")
    with rc:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↺", use_container_width=True, key="refresh_urls"):
            st.rerun()

    show_inactive = st.checkbox("show inactive links", value=True)

    _, urls_resp = api("GET", "/urls", BASE)
    if isinstance(urls_resp, list):
        urls = urls_resp
    elif isinstance(urls_resp, dict) and "urls" in urls_resp:
        urls = urls_resp["urls"]
    else:
        urls = []

    if not urls:
        st.markdown(
            '<div class="alert-warn" style="margin-top:1rem;">'
            'No URLs found — run POST /seed or shorten a URL first</div>',
            unsafe_allow_html=True,
        )
    else:
        if not show_inactive:
            urls = [u for u in urls if u.get("is_active", True)]
        if search:
            q    = search.lower()
            urls = [u for u in urls if
                    q in u.get("short_code", "").lower() or
                    q in u.get("original_url", "").lower() or
                    q in (u.get("title") or "").lower()]

        def sk(u): return u.get("created_at") or ""
        if sort_by == "newest first":
            urls = sorted(urls, key=sk, reverse=True)
        elif sort_by == "oldest first":
            urls = sorted(urls, key=sk)
        elif sort_by == "code a→z":
            urls = sorted(urls, key=lambda u: u.get("short_code", "").lower())
        elif sort_by == "active first":
            urls = sorted(urls, key=lambda u: (not u.get("is_active", True), u.get("short_code", "")))

        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.68rem;'
            f'color:var(--text-xxdim);margin-bottom:0.5rem;">'
            f'{len(urls)} result{"s" if len(urls) != 1 else ""}</div>',
            unsafe_allow_html=True,
        )
        # column headers
        st.markdown(
            '<div style="display:flex;gap:0.8rem;padding:0 1rem 0.3rem;">'
            '<span class="col-header" style="min-width:88px;">CODE</span>'
            '<span class="col-header" style="flex:1;">DESTINATION</span>'
            '<span class="col-header" style="min-width:100px;text-align:right;">TITLE</span>'
            '<span class="col-header" style="min-width:50px;text-align:right;">USER</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        for u in urls:
            code   = u.get("short_code", "")
            orig   = u.get("original_url", "")
            ttl    = u.get("title") or ""
            active = u.get("is_active", True)
            owner  = u.get("user_id", "")
            if isinstance(owner, dict):
                owner = owner.get("username", str(owner))
            dot = "dot-active" if active else "dot-inactive"
            st.markdown(
                f'<div class="url-row">'
                f'<span class="{dot}"></span>'
                f'<span class="code-badge">{code}</span>'
                f'<span class="orig-url" title="{orig}">{orig}</span>'
                f'<span class="url-title-cell">{ttl[:20] + "…" if len(ttl) > 20 else ttl}</span>'
                f'<span class="owner-cell">#{owner}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
