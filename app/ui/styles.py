import streamlit as st

# ── theme helpers ─────────────────────────────────────────────────────────────

def get_theme() -> str:
    """Return 'dark' or 'light' from session_state."""
    return st.session_state.get("theme", "dark")

def toggle_theme():
    st.session_state["theme"] = "light" if get_theme() == "dark" else "dark"

# ── theme token sets (injected directly from Python — no JS needed) ───────────

_DARK_VARS = """
    --bg:           #0c0c0e;
    --bg-sidebar:   #0f0f12;
    --bg-element:   #111115;
    --border:       #2a2a32;
    --border-hover: #3c3c48;
    --text:         #f0f0f8;
    --text-muted:   #b8b8c8;
    --text-dim:     #a0a0b4;
    --text-xdim:    #c0c0d0;
    --text-xxdim:   #7a7a90;
    --text-xxxdim:  #50505e;
    --accent:       #4ade80;
    --accent-hover: #6de896;
    --accent-dim:   #4ade80;
    --accent-bg:    #0a1a0e;
    --accent-border:#1e4a28;
    --accent-btn-fg:#060e08;
    --err:          #f87171;
    --err-bg:       #150c0c;
    --err-border:   #3a1414;
    --warn:         #fbbf24;
    --warn-bg:      #14120a;
    --warn-border:  #3a2e0e;
"""

_LIGHT_VARS = """
    --bg:           #f4f4f7;
    --bg-sidebar:   #eaeaee;
    --bg-element:   #ffffff;
    --border:       #d4d4dc;
    --border-hover: #a0a0b0;
    --text:         #111118;
    --text-muted:   #44444f;
    --text-dim:     #5c5c6a;
    --text-xdim:    #6e6e7c;
    --text-xxdim:   #9090a0;
    --text-xxxdim:  #b8b8c8;
    --accent:       #16a34a;
    --accent-hover: #15803d;
    --accent-dim:   #14532d;
    --accent-bg:    #f0fdf4;
    --accent-border:#86efac;
    --accent-btn-fg:#ffffff;
    --err:          #dc2626;
    --err-bg:       #fef2f2;
    --err-border:   #fca5a5;
    --warn:         #b45309;
    --warn-bg:      #fffbeb;
    --warn-border:  #fcd34d;
"""

# ── component CSS (uses vars only — theme-agnostic) ───────────────────────────

_COMPONENT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Sora:wght@300;400;500;600&display=swap');

/* ── hide streamlit chrome (targeted — keeps sidebar toggles intact) ─── */
#MainMenu                                { display: none !important; }
footer                                   { display: none !important; }
.stDeployButton                          { display: none !important; }
[data-testid="stAppDeployButton"]        { display: none !important; }
[data-testid="stMainMenuButton"]         { display: none !important; }
[data-testid="stDecoration"]             { display: none !important; }
[data-testid="stStatusWidget"]           { display: none !important; }
/* make header transparent instead of hidden — avoids cascade */
header[data-testid="stHeader"]           { background: transparent !important; }

/* ── keep sidebar toggle buttons fully visible & clickable ─────────── */
button[data-testid="stExpandSidebarButton"],
button[data-testid="stBaseButton-headerNoPadding"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    z-index: 9999 !important;
}
[data-testid="stSidebarHeader"]              { visibility: visible !important; }
[data-testid="stSidebarCollapsedControl"]    { visibility: visible !important; display: flex !important; }

/* ── base layout ─────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
    transition: background 0.2s ease, color 0.2s ease;
}
.stApp {
    background: var(--bg) !important;
    color: var(--text) !important;
}
.block-container { padding: 2rem 2.5rem 4rem 2.5rem !important; max-width: 960px !important; }

/* ── sidebar ─────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1.2rem !important; }

/* ── tabs ────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] { border-bottom: 1px solid var(--border) !important; gap: 0 !important; }
[data-testid="stTabs"] [role="tab"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.08em !important;
    color: var(--text-dim) !important;
    padding: 0.5rem 1.2rem !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: transparent !important;
}

/* ── inputs ──────────────────────────────────────── */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    background: var(--bg-element) !important;
    border: 1px solid var(--border) !important;
    border-radius: 7px !important;
    color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.83rem !important;
    transition: border-color 0.15s !important;
}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(74,222,128,0.12) !important;
}
[data-testid="stTextInput"] label, [data-testid="stTextArea"] label,
[data-testid="stSelectbox"] label, [data-testid="stCheckbox"] label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.1em !important;
    color: var(--text-xdim) !important;
    text-transform: uppercase !important;
}

/* ── selectbox ───────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: var(--bg-element) !important;
    border: 1px solid var(--border) !important;
    border-radius: 7px !important;
    color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.83rem !important;
}

/* ── buttons ─────────────────────────────────────── */
.stButton > button {
    background: var(--accent) !important;
    color: var(--accent-btn-fg) !important;
    border: none !important;
    border-radius: 7px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.05em !important;
    padding: 0.5rem 1.2rem !important;
    transition: background 0.15s !important;
}
.stButton > button:hover { background: var(--accent-hover) !important; }
.stButton > button[kind="secondary"] {
    background: var(--bg-element) !important;
    color: var(--text-muted) !important;
    border: 1px solid var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
    color: var(--text) !important;
    border-color: var(--border-hover) !important;
}

/* ── metrics ─────────────────────────────────────── */
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: var(--accent) !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Sora', sans-serif !important;
    font-size: 0.72rem !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

/* ── misc streamlit elements ─────────────────────── */
.stSpinner > div { border-top-color: var(--accent) !important; }
.stRadio label   { font-family: 'JetBrains Mono', monospace !important; font-size: 0.8rem !important; color: var(--text-muted) !important; }
[data-testid="stCheckbox"] label { color: var(--text-muted) !important; }
p, li, .stMarkdown p { color: var(--text) !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: var(--text-muted) !important; }
.stCode pre, .stCode code { background: var(--bg-element) !important; color: var(--text) !important; }

/* ── custom component classes ────────────────────── */
.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-xxdim);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin: 1.4rem 0 0.7rem 0;
}
.url-row {
    display: flex; align-items: center; gap: 0.8rem;
    background: var(--bg-element);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    transition: border-color 0.15s;
}
.url-row:hover { border-color: var(--border-hover); }
.dot-active    { width:7px;height:7px;border-radius:50%;background:var(--accent);flex-shrink:0; }
.dot-inactive  { width:7px;height:7px;border-radius:50%;background:var(--border-hover);flex-shrink:0; }
.code-badge    { font-family:'JetBrains Mono',monospace;font-size:0.85rem;font-weight:700;color:var(--accent);min-width:88px;white-space:nowrap; }
.orig-url      { font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:var(--text-muted);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.url-title-cell{ font-size:0.75rem;color:var(--text-xdim);min-width:100px;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.owner-cell    { font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--text-xxdim);min-width:50px;text-align:right; }
.col-header    { font-family:'JetBrains Mono',monospace;font-size:0.6rem;color:var(--text-xxdim);letter-spacing:0.12em; }

.alert-err  { background:var(--err-bg);border:1px solid var(--err-border);border-radius:7px;padding:0.65rem 0.9rem;font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:var(--err);margin:0.5rem 0; }
.alert-ok   { background:var(--accent-bg);border:1px solid var(--accent-border);border-radius:7px;padding:0.65rem 0.9rem;font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:var(--accent);margin:0.5rem 0; }
.alert-warn { background:var(--warn-bg);border:1px solid var(--warn-border);border-radius:7px;padding:0.65rem 0.9rem;font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:var(--warn);margin:0.5rem 0; }

.result-box   { background:var(--accent-bg);border:1px solid var(--accent-border);border-radius:8px;padding:1rem 1.2rem;margin:0.8rem 0; }
.result-label { font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:var(--accent-dim);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.3rem; }
.result-link  { font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:700;color:var(--accent); }

.health-ok  { display:inline-flex;align-items:center;gap:6px;font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--accent);background:var(--accent-bg);border:1px solid var(--accent-border);border-radius:5px;padding:3px 10px; }
.health-err { display:inline-flex;align-items:center;gap:6px;font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--err);background:var(--err-bg);border:1px solid var(--err-border);border-radius:5px;padding:3px 10px; }
.health-dot-ok  { width:6px;height:6px;border-radius:50%;background:var(--accent);display:inline-block; }
.health-dot-err { width:6px;height:6px;border-radius:50%;background:var(--err);display:inline-block; }
hr.divider { border:none;border-top:1px solid var(--border);margin:1.5rem 0; }
"""


def apply_styles():
    """Inject theme vars + component CSS. No JS — vars chosen in Python."""
    theme = get_theme()
    vars_block = _DARK_VARS if theme == "dark" else _LIGHT_VARS

    css = f"""
{_COMPONENT_CSS}

/* ── active theme tokens ─────────────────────────── */
:root {{
{vars_block}
}}
/* make sure .stApp inherits the token background */
.stApp, section[data-testid="stSidebar"] {{
    background: var(--bg) !important;
}}
"""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
