import streamlit as st

def get_theme():
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "dark"
    return st.session_state.theme_mode

def toggle_theme():
    st.session_state.theme_mode = "light" if get_theme() == "dark" else "dark"

def apply_styles():
    theme = get_theme()
    
    # Define design tokens
    if theme == "dark":
        # Professional Dark - Deep Charcoal & Emerald
        bg, text, accent = "#0c0c0e", "#e2e0db", "#4ade80"
        bg_sid, bg_sec, bg_hvr = "#0f0f12", "#111115", "#1c1c21"
        border, text_dim, text_xdim = "#1c1c21", "#6b6b74", "#3d3d45"
        alert_err, alert_ok, alert_warn = "#f87171", "#4ade80", "#fbbf24"
    else:
        # Professional Light - Snow & Forest
        bg, text, accent = "#ffffff", "#1e1e21", "#059669"
        bg_sid, bg_sec, bg_hvr = "#f9fafb", "#f3f4f6", "#e5e7eb"
        border, text_dim, text_xdim = "#e5e7eb", "#6b7280", "#9ca3af"
        alert_err, alert_ok, alert_warn = "#dc2626", "#059669", "#d97706"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Sora:wght@300;400;500;600&display=swap');

    :root {{
        --bg: {bg}; --text: {text}; --accent: {accent};
        --bg-sidebar: {bg_sid}; --bg-secondary: {bg_sec}; --bg-hover: {bg_hvr};
        --border: {border}; --text-dim: {text_dim}; --text-xdim: {text_xdim};
        --alert-err: {alert_err}; --alert-ok: {alert_ok}; --alert-warn: {alert_warn};
    }}

    html, body, [class*="css"] {{ font-family: 'Sora', sans-serif; }}
    .stApp {{ background: var(--bg); color: var(--text); transition: background 0.3s ease; }}
    .block-container {{ padding: 2rem 2.5rem 4rem 2.5rem !important; max-width: 960px !important; }}

    section[data-testid="stSidebar"] {{
        background: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border) !important;
    }}
    section[data-testid="stSidebar"] .block-container {{ padding: 1.5rem 1.2rem !important; }}

    [data-testid="stTabs"] [role="tablist"] {{ border-bottom: 1px solid var(--border) !important; gap: 0 !important; }}
    [data-testid="stTabs"] [role="tab"] {{
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.75rem !important;
        letter-spacing: 0.08em !important; color: var(--text-dim) !important;
        padding: 1rem 1.2rem !important; border-radius: 0 !important;
        border-bottom: 2px solid transparent !important; transition: all 0.2s ease;
    }}
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
        color: var(--accent) !important; border-bottom: 2px solid var(--accent) !important;
        background: transparent !important; font-weight: 700 !important;
    }}

    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {{
        background: var(--bg-secondary) !important; border: 1px solid var(--border) !important;
        border-radius: 8px !important; color: var(--text) !important;
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.85rem !important;
        padding: 0.6rem 0.8rem !important; transition: border-color 0.2s ease;
    }}
    [data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {{
        border-color: var(--accent) !important; box-shadow: 0 0 0 2px rgba(74,222,128,0.1) !important;
    }}
    [data-testid="stTextInput"] label, [data-testid="stTextArea"] label,
    [data-testid="stSelectbox"] label, [data-testid="stCheckbox"] label {{
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.7rem !important;
        letter-spacing: 0.1em !important; color: var(--text-xdim) !important; text-transform: uppercase !important;
        margin-bottom: 0.4rem !important;
    }}

    .stButton > button {{
        background: var(--accent) !important; color: #ffffff !important; border: none !important;
        border-radius: 8px !important; font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important; font-size: 0.8rem !important; letter-spacing: 0.05em !important;
        padding: 0.6rem 1.4rem !important; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        text-transform: uppercase !important;
    }}
    .stButton > button:hover {{ transform: translateY(-1px); filter: brightness(1.1); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
    .stButton > button[kind="secondary"] {{
        background: var(--bg-sidebar) !important; color: var(--text-dim) !important; border: 1px solid var(--border) !important;
    }}
    .stButton > button[kind="secondary"]:hover {{ color: var(--text) !important; border-color: var(--text-xdim) !important; }}

    [data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.8rem !important; font-weight: 700 !important; color: var(--accent) !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-family: 'Sora', sans-serif !important; font-size: 0.75rem !important;
        color: var(--text-dim) !important; text-transform: uppercase !important; letter-spacing: 0.08em !important;
    }}

    .section-label {{
        font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; color: var(--text-xdim);
        letter-spacing: 0.14em; text-transform: uppercase; margin: 1.8rem 0 0.8rem 0; opacity: 0.7;
    }}
    .url-row {{
        display: flex; align-items: center; gap: 0.8rem;
        background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 9px;
        padding: 0.85rem 1.2rem; margin-bottom: 0.6rem; transition: all 0.2s ease;
    }}
    .url-row:hover {{ border-color: var(--text-xdim); background: var(--bg-hover); transform: translateX(2px); }}
    .dot-active  {{ width:8px;height:8px;border-radius:50%;background:var(--alert-ok);flex-shrink:0; box-shadow: 0 0 8px var(--alert-ok); }}
    .dot-inactive{{ width:8px;height:8px;border-radius:50%;background:var(--text-xdim);flex-shrink:0; }}
    .code-badge  {{ font-family:'JetBrains Mono',monospace;font-size:0.85rem;font-weight:700;color:var(--accent);min-width:88px; }}
    .orig-url    {{ font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:var(--text-dim);flex:1; }}
    .url-title-cell {{ font-size:0.75rem;color:var(--text-xdim);min-width:100px;text-align:right; }}
    .owner-cell  {{ font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--text-xdim);min-width:50px;text-align:right; opacity:0.6; }}

    .alert-err  {{ background: rgba(248,113,113,0.05); border: 1px solid var(--alert-err); border-radius:8px; padding:0.8rem 1rem; font-family:'JetBrains Mono',monospace; font-size:0.78rem; color: var(--alert-err); margin:0.8rem 0; }}
    .alert-ok   {{ background: rgba(74,222,128,0.05); border: 1px solid var(--alert-ok); border-radius:8px; padding:0.8rem 1rem; font-family:'JetBrains Mono',monospace; font-size:0.8rem; color: var(--alert-ok); margin:0.8rem 0; }}
    .alert-warn {{ background: rgba(251,191,36,0.05); border: 1px solid var(--alert-warn); border-radius:8px; padding:0.8rem 1rem; font-family:'JetBrains Mono',monospace; font-size:0.78rem; color: var(--alert-warn); margin:0.8rem 0; }}

    .result-box  {{ background: var(--bg-sidebar); border: 1px solid var(--accent); border-radius:10px; padding:1.2rem 1.5rem; margin:1.2rem 0; box-shadow: 0 8px 24px rgba(0,0,0,0.1); }}
    .result-label{{ font-family:'JetBrains Mono',monospace; font-size:0.65rem; color: var(--accent); letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem; opacity:0.8; }}
    .result-link {{ font-family:'JetBrains Mono',monospace; font-size:1.15rem; font-weight:700; color: var(--accent); }}

    .health-ok  {{ display:inline-flex;align-items:center;gap:6px;font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:var(--alert-ok);background:rgba(74,222,128,0.05);border:1px solid var(--alert-ok);border-radius:20px;padding:4px 12px; }}
    .health-err {{ display:inline-flex;align-items:center;gap:6px;font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:var(--alert-err);background:rgba(248,113,113,0.05);border:1px solid var(--alert-err);border-radius:20px;padding:4px 12px; }}
    .health-dot-ok  {{ width:6px;height:6px;border-radius:50%;background:var(--alert-ok);display:inline-block; }}
    .health-dot-err {{ width:6px;height:6px;border-radius:50%;background:var(--alert-err);display:inline-block; }}
    hr.divider {{ border:none; border-top:1px solid var(--border); margin:2rem 0; }}
    
    /* Chrome Stripping */
    #MainMenu, footer {{ visibility: hidden !important; }}
    header[data-testid="stHeader"] {{ background: transparent !important; border:none !important; }}
    </style>
    """, unsafe_allow_html=True)
