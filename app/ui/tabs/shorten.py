import streamlit as st
import json
from app.ui.helpers import api, gen_code

def render_tab_shorten(BASE, user_map):
    st.markdown('<div class="section-label">— new short link</div>', unsafe_allow_html=True)

    r1c1, r1c2 = st.columns([3, 1])
    with r1c1:
        dest = st.text_input("DESTINATION URL", placeholder="https://github.com/MLH/mlh-policies")
    with r1c2:
        custom_code = st.text_input("SHORT CODE", placeholder="auto-generated", max_chars=12,
                                     help="Leave blank for a random 6-char code")

    r2c1, r2c2, r2c3 = st.columns([2, 2, 1])
    with r2c1:
        title = st.text_input("TITLE", placeholder="MLH Policies")
    with r2c2:
        if user_map:
            owner_label = st.selectbox("OWNER", list(user_map.keys()))
            owner_id = user_map[owner_label]
        else:
            st.markdown('<div class="alert-warn">No users exist.</div>', unsafe_allow_html=True)
            if st.button("Seed Demo Data Now", use_container_width=True, key="shorten_seed_btn"):
                s, r = api("POST", "/seed", BASE)
                if s in (200, 201):
                    st.success("Seeded successfully, refresh the page.")
                else:
                    st.error("Seed failed. Backend offline?")
            owner_id = None
    with r2c3:
        st.markdown("<br>", unsafe_allow_html=True)
        do_shorten = st.button("shorten →", use_container_width=True, key="shorten_btn")

    if do_shorten:
        if not dest:
            st.markdown('<div class="alert-err">destination url is required</div>', unsafe_allow_html=True)
        elif not dest.startswith(("http://", "https://")):
            st.markdown('<div class="alert-err">url must start with http:// or https://</div>', unsafe_allow_html=True)
        elif not owner_id:
            st.markdown('<div class="alert-err">select an owner user first</div>', unsafe_allow_html=True)
        else:
            code = custom_code.strip() if custom_code.strip() else gen_code()
            payload = {
                "original_url": dest,
                "short_code": code,
                "user_id": owner_id,
                "title": title.strip() or None,
                "is_active": True,
            }
            with st.spinner("creating…"):
                sc, rv = api("POST", "/shorten", BASE, json=payload)
            if sc in (200, 201):
                short_link = f"{BASE}/{code}"
                st.markdown(
                    f'<div class="result-box">'
                    f'<div class="result-label">short link created</div>'
                    f'<div class="result-link">{short_link}</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:var(--accent);margin-top:0.3rem;opacity:0.8;">'
                    f'→ {dest[:80]}{"…" if len(dest)>80 else ""}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f'<div class="alert-err">error: {rv.get("error", json.dumps(rv))}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label" style="margin-top:2rem;">— quick reference</div>', unsafe_allow_html=True)
    st.code(f"""# shorten
curl -X POST {BASE}/shorten \\
  -H 'Content-Type: application/json' \\
  -d '{{"original_url":"https://example.com","short_code":"abc123","user_id":1}}'

# health / ready / stats
curl {BASE}/health
curl {BASE}/ready
curl {BASE}/stats

# seed demo data
curl -X POST {BASE}/seed""", language="bash")
