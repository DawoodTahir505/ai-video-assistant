import shutil
import tempfile
from pathlib import Path
from html import escape

import streamlit as st
from dotenv import load_dotenv

from audio_processor import download_youtube_audio
from transcriber import transcribe_all
from summarizer import summarize, generate_title
from rag_engine import build_rag_chain, ask_question

load_dotenv()

MEDIA_TYPES = ["mp3", "wav", "m4a", "mp4", "mkv", "webm", "ogg", "flac"]
SUGGESTIONS = [
    "What are the key points?",
    "What is the main conclusion?",
    "Who is speaking and about what?",
]


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="AI Video Assistant",
    page_icon="▶",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    :root {
        --ink: #0f1b2d;
        --body: #3d4859;
        --muted: #6b7686;
        --line: #e2e6ec;
        --paper: #f5f7fa;
        --card: #ffffff;
        --accent: #3347d6;
        --accent-dark: #2837b0;
        --accent-soft: #eceffd;
    }

    html, body, .stApp, [class*="css"] {
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
        color: var(--body);
    }
    .stApp { background: var(--paper); }

    .main .block-container {
        max-width: 760px;
        padding: 56px 24px 120px 24px;
    }

    #MainMenu, footer, [data-testid="stSidebar"],
    [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
    header { background: transparent !important; }

    :focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px; }

    /* ---------- Brand ---------- */
    .brand {
        display: flex; align-items: center; gap: 10px;
        font-size: 15px; font-weight: 700; color: var(--ink);
        margin-bottom: 44px;
    }
    .brand-mark {
        width: 30px; height: 30px; border-radius: 9px;
        display: inline-flex; align-items: center; justify-content: center;
        background: var(--accent); color: #fff; font-size: 11px; padding-left: 2px;
    }

    /* ---------- Hero ---------- */
    .hero-title {
        font-size: clamp(38px, 7vw, 60px); line-height: 1.04;
        letter-spacing: -2.2px; font-weight: 800; color: var(--ink);
        margin: 0 0 16px 0; padding: 0;
    }
    .hero-description {
        font-size: 18px; line-height: 1.6; color: var(--muted);
        max-width: 520px; margin-bottom: 36px;
    }

    /* ---------- Input card ---------- */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--card);
        border: 1px solid var(--line) !important;
        border-radius: 18px !important;
        box-shadow: 0 1px 2px rgba(15, 27, 45, 0.04), 0 8px 24px rgba(15, 27, 45, 0.05);
    }

    .stTextInput input {
        border-radius: 12px !important; border: 1px solid var(--line) !important;
        min-height: 50px; background: var(--paper) !important;
        font-size: 15px; padding: 0 16px !important;
    }
    .stTextInput input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-soft) !important;
    }

    [data-testid="stFileUploader"] section {
        border: 1.5px dashed #c8cfda; border-radius: 12px; background: var(--paper);
    }

    /* ---------- Tabs ---------- */
    .stTabs [data-baseweb="tab-list"] { gap: 26px; border-bottom: 1px solid var(--line); }
    .stTabs [data-baseweb="tab"] {
        padding: 12px 0; font-weight: 600; font-size: 15px; color: var(--muted);
    }
    .stTabs [aria-selected="true"] { color: var(--ink); }
    .stTabs [data-baseweb="tab-highlight"] { background: var(--accent); height: 2px; }

    /* ---------- Buttons ---------- */
    .stButton > button {
        border-radius: 12px !important; min-height: 48px;
        font-weight: 600; font-family: inherit;
        border: 1px solid var(--line); background: var(--card); color: var(--ink);
        transition: background .15s, border-color .15s;
    }
    .stButton > button:hover { border-color: var(--accent); color: var(--accent); }
    .stButton > button[kind="primary"] {
        background: var(--accent); border: 1px solid var(--accent); color: #fff;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--accent-dark); border-color: var(--accent-dark); color: #fff;
    }

    /* ---------- Result header ---------- */
    .result-label { color: var(--muted); font-size: 13px; font-weight: 600; margin-bottom: 8px; }
    .result-title {
        font-size: clamp(26px, 4.6vw, 36px); line-height: 1.18;
        letter-spacing: -1px; font-weight: 800; color: var(--ink);
        margin-bottom: 28px;
    }

    /* ---------- Summary ---------- */
    .summary-wrap { padding: 12px 10px; }
    .summary-wrap p, .summary-wrap li {
        font-size: 16.5px; line-height: 1.8; color: var(--ink);
    }
    .summary-wrap li { margin-bottom: 6px; }

    /* ---------- Chat ---------- */
    .chat-intro { color: var(--muted); font-size: 14.5px; margin: 18px 0 12px 0; }

    [data-testid="stChatMessage"] {
        background: var(--card); border: 1px solid var(--line);
        border-radius: 14px; padding: 16px 18px; margin-bottom: 12px;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: var(--accent-soft); border-color: transparent;
    }
    [data-testid="stChatInput"] {
        border-radius: 14px !important; border: 1px solid var(--line) !important;
        background: var(--card);
    }

    /* ---------- Progress ---------- */
    .stProgress > div > div > div > div { background: var(--accent); }

    @media (max-width: 760px) {
        .main .block-container { padding: 32px 16px 100px 16px; }
        .brand { margin-bottom: 30px; }
        .hero-description { font-size: 16.5px; }
    }
    @media (prefers-reduced-motion: reduce) {
        * { transition: none !important; animation: none !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# STATE
# ============================================================

def init_session_state():
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("pending_question", None)


def reset():
    st.session_state.result = None
    st.session_state.history = []
    st.session_state.pending_question = None


# ============================================================
# PIPELINE
# ============================================================

def get_audio(source: str, uploaded_file, temp_dirs: list) -> str:
    if uploaded_file is not None:
        temp_dir = tempfile.mkdtemp(prefix="AI_VIDEO_ASSISTANT_")
        temp_dirs.append(temp_dir)
        path = Path(temp_dir) / Path(uploaded_file.name).name
        path.write_bytes(uploaded_file.getbuffer())
        return str(path)

    source = source.strip()

    if source.startswith("http"):
        audio_path = download_youtube_audio(source)
        temp_dir = tempfile.mkdtemp(prefix="AI_VIDEO_ASSISTANT_")
        temp_dirs.append(temp_dir)
        return shutil.move(audio_path, temp_dir)

    if not Path(source).exists():
        raise FileNotFoundError(f"File not found: {source}")

    return source


def analyze_input(source: str, uploaded_file) -> None:
    temp_dirs = []
    progress = st.progress(0, text="Preparing your video...")

    try:
        progress.progress(5, text="Loading audio...")
        audio_file = get_audio(source, uploaded_file, temp_dirs)

        progress.progress(20, text="Transcribing...")
        transcript = transcribe_all([audio_file])
        if not transcript:
            raise RuntimeError("No speech found in the audio.")

        progress.progress(50, text="Writing title...")
        title = generate_title(transcript).strip()

        progress.progress(65, text="Summarizing...")
        summary = summarize(transcript)

        progress.progress(95, text="Preparing chat...")
        rag_chain = build_rag_chain(transcript)

        progress.progress(100, text="Done")
    finally:
        for d in temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    st.session_state.result = {
        "title": title,
        "summary": summary,
        "rag_chain": rag_chain,
    }
    st.session_state.history = []


# ============================================================
# LANDING
# ============================================================

def show_brand():
    st.markdown(
        '<div class="brand"><span class="brand-mark">▶</span>AI Video Assistant</div>',
        unsafe_allow_html=True,
    )


def show_landing():
    st.markdown(
        """
        <h1 class="hero-title">Understand any video in minutes.</h1>
        <div class="hero-description">
            Add a video or audio file to get a clear summary,
            then ask questions about it in plain language.
        </div>
        """,
        unsafe_allow_html=True,
    )

    source, uploaded_file = "", None

    with st.container(border=True):
        tab_link, tab_file = st.tabs(["YouTube link", "Upload file"])

        with tab_link:
            source = st.text_input(
                "YouTube URL or local path",
                placeholder="Paste a YouTube link",
                label_visibility="collapsed",
            )

        with tab_file:
            uploaded_file = st.file_uploader(
                "Upload video or audio",
                type=MEDIA_TYPES,
                label_visibility="collapsed",
            )

        clicked = st.button("Analyze video", type="primary", use_container_width=True)

    if not clicked:
        return

    if not source.strip() and uploaded_file is None:
        st.error("Paste a YouTube link or upload a video or audio file.")
        return

    try:
        analyze_input(source, uploaded_file)
    except Exception as error:
        st.error(f"Analysis failed: {error}")
    else:
        st.rerun()


# ============================================================
# RESULT
# ============================================================

def show_result_header(result):
    title = escape(str(result.get("title", "Video analysis")))

    col_text, col_btn = st.columns([4, 1], vertical_alignment="top")
    with col_text:
        st.markdown(
            f"""
            <div class="result-label">Analysis</div>
            <div class="result-title">{title}</div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("New video", use_container_width=True):
            reset()
            st.rerun()


def show_summary(result):
    with st.container(border=True):
        st.markdown('<div class="summary-wrap">', unsafe_allow_html=True)
        st.markdown(result.get("summary", ""))
        st.markdown("</div>", unsafe_allow_html=True)


def show_chat(result):
    if not st.session_state.history:
        st.markdown(
            '<div class="chat-intro">Ask anything about this video, or start with one of these:</div>',
            unsafe_allow_html=True,
        )
        for i, suggestion in enumerate(SUGGESTIONS):
            if st.button(suggestion, key=f"suggest_{i}", use_container_width=True):
                st.session_state.pending_question = suggestion
                st.rerun()

    for message in st.session_state.history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask a question about this video")

    if not question:
        question = st.session_state.pending_question

    if not question:
        return

    st.session_state.pending_question = None

    try:
        with st.spinner("Thinking..."):
            answer = ask_question(result["rag_chain"], question, st.session_state.history)
    except Exception as error:
        st.error(f"Could not answer this question: {error}")
        return

    st.session_state.history.append({"role": "user", "content": question})
    st.session_state.history.append({"role": "assistant", "content": answer})
    st.rerun()


# ============================================================
# MAIN
# ============================================================

def main():
    init_session_state()
    show_brand()

    result = st.session_state.result

    if result is None:
        show_landing()
        return

    show_result_header(result)

    tab_summary, tab_chat = st.tabs(["Summary", "Ask questions"])

    with tab_summary:
        show_summary(result)

    with tab_chat:
        show_chat(result)


if __name__ == "__main__":
    main()
