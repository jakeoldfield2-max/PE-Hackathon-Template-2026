import streamlit as st

def apply_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Sora:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Sora', sans-serif; }
    .stApp { background: #0c0c0e; color: #e2e0db; }
    .block-container { padding: 2rem 2.5rem 4rem 2.5rem !important; max-width: 960px !important; }

    section[data-testid="stSidebar"] {
        background: #0f0f12 !important;
        border-right: 1px solid #1c1c21 !important;
    }
    section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1.2rem !important; }

    [data-testid="stTabs"] [role="tablist"] { border-bottom: 1px solid #1c1c21 !important; gap: 0 !important; }
    [data-testid="stTabs"] [role="tab"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.08em !important;
        color: #4a4a52 !important;
        padding: 0.5rem 1.2rem !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        color: #4ade80 !important;
        border-bottom: 2px solid #4ade80 !important;
        background: transparent !important;
    }

    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
        background: #111115 !important; border: 1px solid #1c1c21 !important;
        border-radius: 7px !important; color: #e2e0db !important;
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.83rem !important;
    }
    [data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
        border-color: #4ade80 !important; box-shadow: 0 0 0 2px rgba(74,222,128,0.07) !important;
    }
    [data-testid="stTextInput"] label, [data-testid="stTextArea"] label,
    [data-testid="stSelectbox"] label, [data-testid="stCheckbox"] label {
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.68rem !important;
        letter-spacing: 0.1em !important; color: #3d3d45 !important; text-transform: uppercase !important;
    }

    [data-testid="stSelectbox"] > div > div {
        background: #111115 !important; border: 1px solid #1c1c21 !important;
        border-radius: 7px !important; color: #e2e0db !important;
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.83rem !important;
    }

    .stButton > button {
        background: #4ade80 !important; color: #060e08 !important; border: none !important;
        border-radius: 7px !important; font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important; font-size: 0.78rem !important; letter-spacing: 0.05em !important;
        padding: 0.5rem 1.2rem !important; transition: background 0.15s !important;
    }
    .stButton > button:hover { background: #6de896 !important; }
    .stButton > button[kind="secondary"] {
        background: #111115 !important; color: #6b6b74 !important; border: 1px solid #1c1c21 !important;
    }
    .stButton > button[kind="secondary"]:hover { color: #e2e0db !important; border-color: #2c2c35 !important; }

    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.6rem !important; font-weight: 700 !important; color: #4ade80 !important;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Sora', sans-serif !important; font-size: 0.72rem !important;
        color: #4a4a52 !important; text-transform: uppercase !important; letter-spacing: 0.08em !important;
    }

    .stSpinner > div { border-top-color: #4ade80 !important; }
    .stRadio label { font-family: 'JetBrains Mono', monospace !important; font-size: 0.8rem !important; color: #6b6b74 !important; }

    .section-label {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #2e2e38;
        letter-spacing: 0.14em; text-transform: uppercase; margin: 1.4rem 0 0.7rem 0;
    }
    .url-row {
        display: flex; align-items: center; gap: 0.8rem;
        background: #111115; border: 1px solid #1c1c21; border-radius: 8px;
        padding: 0.75rem 1rem; margin-bottom: 0.5rem;
    }
    .url-row:hover { border-color: #2c2c35; }
    .dot-active  { width:7px;height:7px;border-radius:50%;background:#4ade80;flex-shrink:0; }
    .dot-inactive{ width:7px;height:7px;border-radius:50%;background:#2c2c35;flex-shrink:0; }
    .code-badge  { font-family:'JetBrains Mono',monospace;font-size:0.85rem;font-weight:700;color:#4ade80;min-width:88px;white-space:nowrap; }
    .orig-url    { font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:#6b6b74;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
    .url-title-cell { font-size:0.75rem;color:#3d3d45;min-width:100px;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
    .owner-cell  { font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:#2e2e38;min-width:50px;text-align:right; }

    .alert-err  { background:#150c0c;border:1px solid #3a1414;border-radius:7px;padding:0.65rem 0.9rem;font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:#f87171;margin:0.5rem 0; }
    .alert-ok   { background:#091409;border:1px solid #1a4020;border-radius:7px;padding:0.65rem 0.9rem;font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:#4ade80;margin:0.5rem 0; }
    .alert-warn { background:#14120a;border:1px solid #3a2e0e;border-radius:7px;padding:0.65rem 0.9rem;font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:#fbbf24;margin:0.5rem 0; }

    .result-box  { background:#091409;border:1px solid #1a4020;border-radius:8px;padding:1rem 1.2rem;margin:0.8rem 0; }
    .result-label{ font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#2e7040;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.3rem; }
    .result-link { font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:700;color:#4ade80; }

    .health-ok  { display:inline-flex;align-items:center;gap:6px;font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:#4ade80;background:#091409;border:1px solid #1a4020;border-radius:5px;padding:3px 10px; }
    .health-err { display:inline-flex;align-items:center;gap:6px;font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:#f87171;background:#150c0c;border:1px solid #3a1414;border-radius:5px;padding:3px 10px; }
    .health-dot-ok  { width:6px;height:6px;border-radius:50%;background:#4ade80;display:inline-block; }
    .health-dot-err { width:6px;height:6px;border-radius:50%;background:#f87171;display:inline-block; }
    hr.divider { border:none;border-top:1px solid #1c1c21;margin:1.5rem 0; }
    </style>
    """, unsafe_allow_html=True)
