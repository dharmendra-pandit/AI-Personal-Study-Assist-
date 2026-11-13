import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap');

:root {
    --ink: #1F2430;
    --muted: #6B7280;
    --accent: #2B3A67;
    --accent-soft: #E8EBF4;
    --paper: #FAF9F6;
    --surface: #FFFFFF;
    --line: #E6E3DB;
    --ok: #2F6B4F;
    --bad: #9B3B3B;
}

html, body, [class*="css"], .stApp, button, input, textarea, select {
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
}
.stApp { background: var(--paper); color: var(--ink); }

/* chrome */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 860px; padding-top: 3rem; padding-bottom: 5rem; }

/* title */
.app-title {
    font-family: 'Fraunces', Georgia, serif;
    font-size: 2.4rem; font-weight: 600; letter-spacing: -0.02em;
    color: var(--ink); line-height: 1.1;
}
.app-sub { color: var(--muted); font-size: 0.98rem; margin: 0.35rem 0 1.8rem; }

h1, h2, h3 { font-family: 'Fraunces', Georgia, serif; letter-spacing: -0.01em; color: var(--ink); }
h2 { font-size: 1.5rem !important; }
h3 { font-size: 1.2rem !important; }

/* tabs */
.stTabs [data-baseweb="tab-list"] { gap: 1.6rem; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] {
    padding: 0.6rem 0; background: transparent; color: var(--muted);
    font-weight: 500; font-size: 0.95rem;
}
.stTabs [aria-selected="true"] { color: var(--accent); }
.stTabs [data-baseweb="tab-highlight"] { background: var(--accent); height: 2px; }
.stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.6rem; }

/* sidebar */
[data-testid="stSidebar"] { background: #F2F0EA; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] h2 {
    font-family: 'Inter', sans-serif; font-size: 0.72rem !important; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted);
}
/* document picker: one checkbox per file, long names wrap instead of overflowing */
[class*="st-key-pick_"] label p { font-size: 0.88rem; overflow-wrap: anywhere; line-height: 1.35; }
[class*="st-key-hist_"] button { padding: 0.2rem 0.3rem; min-height: 0; color: var(--muted); }
.doc-item {
    font-size: 0.88rem; padding: 0.45rem 0.7rem; margin-bottom: 0.35rem;
    background: var(--surface); border: 1px solid var(--line); border-radius: 8px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* buttons */
.stButton button, .stDownloadButton button {
    border-radius: 8px; font-weight: 500; font-size: 0.9rem;
    padding: 0.45rem 1.1rem; border: 1px solid var(--line);
    background: var(--surface); color: var(--ink); box-shadow: none; transition: all .15s ease;
}
.stButton button:hover, .stDownloadButton button:hover {
    border-color: var(--accent); color: var(--accent); background: var(--surface);
}
button[data-testid="stBaseButton-primary"] {
    background: var(--accent); color: #fff; border: 1px solid var(--accent);
}
button[data-testid="stBaseButton-primary"]:hover {
    background: #223056; color: #fff; border-color: #223056;
}

/* inputs */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {
    border-radius: 8px !important; border-color: var(--line) !important; background: var(--surface) !important;
}
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within {
    border-color: var(--accent) !important; box-shadow: 0 0 0 1px var(--accent) !important;
}
label p { font-size: 0.85rem !important; font-weight: 500; color: var(--muted); }
[data-testid="stFileUploaderDropzone"] {
    background: var(--surface); border: 1px dashed #CFCBC0; border-radius: 10px;
}

/* cards */
[data-testid="stExpander"] {
    background: var(--surface); border: 1px solid var(--line) !important; border-radius: 10px;
}
[data-testid="stExpander"] summary { font-weight: 500; }
[data-testid="stMetric"] {
    background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
    padding: 1rem 1.2rem;
}
[data-testid="stMetricLabel"] p {
    font-size: 0.72rem !important; text-transform: uppercase; letter-spacing: 0.08em;
}
[data-testid="stMetricValue"] { font-family: 'Fraunces', Georgia, serif; font-weight: 600; }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }

/* chat */
[data-testid="stChatMessage"] {
    background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
    padding: 1rem 1.2rem; margin-bottom: 0.8rem;
}
[data-testid="stForm"] { border: none; padding: 0; margin-top: 0.4rem; }
/* user turns tinted, assistant turns white; avatars in the app's navy instead of red/orange */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #EEF0F6; border-color: #DDE1EC;
}
[data-testid="stChatMessageAvatarUser"] {
    background-color: var(--accent-soft) !important; color: var(--accent) !important;
}
[data-testid="stChatMessageAvatarAssistant"] {
    background-color: var(--accent) !important; color: #fff !important;
}
[data-testid="stChatMessage"] [data-testid="stCaptionContainer"] { margin-top: -0.3rem; }

/* alerts: quiet, left-accented */
[data-testid="stAlert"] {
    border-radius: 8px; border: 1px solid var(--line); border-left-width: 3px;
    background: var(--surface);
}

/* quiz + plan */
.q-label { font-weight: 600; margin: 1.6rem 0 0.2rem; line-height: 1.45; }
.q-num { color: var(--accent); margin-right: 0.5rem; }
.feedback { font-size: 0.9rem; padding: 0.5rem 0.8rem; border-radius: 8px; margin-top: 0.3rem; }
.feedback.ok { background: #EAF3EE; color: var(--ok); }
.feedback.bad { background: #F7ECEC; color: var(--bad); }
.score {
    font-family: 'Fraunces', Georgia, serif; font-size: 2.2rem; font-weight: 600;
    color: var(--accent); margin-top: 1.4rem;
}
.chip {
    display: inline-block; font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em;
    padding: 0.15rem 0.55rem; border-radius: 999px; background: var(--accent-soft);
    color: var(--accent); margin-right: 0.5rem; vertical-align: middle;
}
.task-desc { color: var(--ink); font-size: 0.92rem; margin: 0.3rem 0 0.15rem; line-height: 1.45; }
.task-ref { color: var(--accent); font-size: 0.82rem; font-weight: 500; }
.task-outcome { color: var(--muted); font-size: 0.84rem; font-style: italic; margin-bottom: 0.9rem; }

/* page navigation (segmented control styled as underline tabs) */
[data-testid="stButtonGroup"], [data-testid="stButtonGroup"] div { gap: 0.4rem; }
[data-testid="stButtonGroup"] { margin-bottom: -0.9rem; }
[data-testid="stButtonGroup"] button {
    background: transparent !important; border: none !important; border-radius: 0 !important;
    border-bottom: 2px solid transparent !important; padding: 0.4rem 0 !important;
    margin-right: 1.8rem !important; min-width: 0 !important; width: auto !important;
    color: var(--muted) !important; font-weight: 500; box-shadow: none !important;
}
[data-testid="stButtonGroup"] button[aria-checked="true"],
[data-testid="stButtonGroup"] button[aria-pressed="true"],
[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] {
    color: var(--accent) !important; border-bottom-color: var(--accent) !important;
}
[data-testid="stProgress"] > div > div > div > div { background-color: var(--accent); }
.empty {
    text-align: center; color: var(--muted); padding: 2.5rem 1rem;
    border: 1px dashed #CFCBC0; border-radius: 12px; background: var(--surface);
}
</style>
"""


def apply():
    st.markdown(CSS, unsafe_allow_html=True)


def empty(message: str):
    st.markdown(f'<div class="empty">{message}</div>', unsafe_allow_html=True)
