import hmac
import shutil
import tempfile
from html import escape
from pathlib import Path

import streamlit as st

from audio_processor import download_audio, prepare_audio
from config import get_secret
from rag_engine import TranscriptIndex, ask_question
from summarizer import generate_title, summarize
from transcriber import transcribe
from translator import LANGUAGES as TARGET_LANGUAGES, to_srt, translate_segments, translate_summary
from utils import fmt_time, transcript_text
from dubber import dub

MEDIA_TYPES = ["mp3", "wav", "m4a", "mp4", "mkv", "webm", "ogg", "flac"]
SUGGESTIONS = [
    "What are the key points?",
    "What is the main conclusion?",
    "Who is speaking and about what?",
]
LANGUAGE = "en"

st.set_page_config(page_title="AI Video Assistant", page_icon="▶", layout="centered",
                   initial_sidebar_state="collapsed")

st.markdown(f"<style>{(Path(__file__).parent / 'style.css').read_text()}</style>",
            unsafe_allow_html=True)


# ---------- state ----------

def init_state():
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("pending_question", None)
    st.session_state.setdefault("authed", False)


def reset():
    st.session_state.result = None
    st.session_state.history = []
    st.session_state.pending_question = None


def show_brand():
    st.markdown('<div class="brand"><span class="brand-mark">▶</span>AI Video Assistant</div>',
                unsafe_allow_html=True)


def require_password():
    password = get_secret("APP_PASSWORD")
    if not password or st.session_state.authed:
        return
    show_brand()
    entered = st.text_input("Password", type="password")
    if entered:
        if hmac.compare_digest(entered, str(password)):
            st.session_state.authed = True
            st.rerun()
        st.error("Incorrect password.")
    st.stop()


# ---------- pipeline ----------

def analyze(source: str, uploaded):
    workdir = Path(tempfile.mkdtemp(prefix="ava_"))
    bar = st.progress(0, text="Preparing...")
    try:
        bar.progress(5, text="Loading media...")
        if uploaded is not None:
            src = workdir / Path(uploaded.name).name
            src.write_bytes(uploaded.getbuffer())
        else:
            src = download_audio(source, workdir)

        bar.progress(15, text="Processing audio...")
        parts = prepare_audio(src, workdir / "parts")

        def on_progress(done, total):
            bar.progress(20 + int(40 * done / total), text=f"Transcribing {done}/{total}...")

        segments = transcribe(parts, LANGUAGE, on_progress)
        if not segments:
            raise RuntimeError("No speech found in the audio.")
        text = transcript_text(segments)

        bar.progress(65, text="Writing title...")
        title = generate_title(text)
        bar.progress(75, text="Summarizing...")
        summary = summarize(text)
        bar.progress(95, text="Preparing chat...")
        index = TranscriptIndex(segments)
        bar.progress(100, text="Done")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        bar.empty()

    st.session_state.result = {
        "title": title, "summary": summary, "segments": segments, "index": index,
        "duration": fmt_time(segments[-1]["end"]), "words": len(text.split()),
    }
    st.session_state.history = []


# ---------- views ----------

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

    source, uploaded = "", None
    with st.container(border=True):
        tab_link, tab_file = st.tabs(["Video link", "Upload file"])
        with tab_link:
            source = st.text_input("Video URL", placeholder="Paste a YouTube link",
                                   label_visibility="collapsed")
        with tab_file:
            uploaded = st.file_uploader("Upload video or audio", type=MEDIA_TYPES,
                                        label_visibility="collapsed")
        clicked = st.button("Analyze video", type="primary", use_container_width=True)

    st.markdown(
        """
        <div class="feats">
            <div class="feat"><b>Summary</b><span>Overview, key points and takeaways.</span></div>
            <div class="feat"><b>Ask questions</b><span>Answers with clickable-style timestamps.</span></div>
            <div class="feat"><b>Translate &amp; dub</b><span>12 languages with subtitles and voice-over.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not clicked:
        return
    if not source.strip() and uploaded is None:
        st.error("Paste a link or upload a file.")
        return

    try:
        analyze(source, uploaded)
    except Exception as error:
        st.error(f"Analysis failed: {error}")
    else:
        st.rerun()


def show_header(result):
    col_text, col_btn = st.columns([4, 1], vertical_alignment="top")
    with col_text:
        st.markdown(
            f'<div class="result-label">Analysis</div>'
            f'<div class="result-title">{escape(result["title"])}</div>'
            f'<div class="meta"><span>{result["duration"]} duration</span>'
            f'<span>{result["words"]:,} words</span><span>English</span></div>',
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("New video", use_container_width=True):
            reset()
            st.rerun()


def show_summary(result):
    with st.container(border=True):
        st.markdown(result["summary"])
    st.download_button("Download summary", f"# {result['title']}\n\n{result['summary']}",
                       file_name="summary.md", mime="text/markdown")


def show_transcript(result):
    text = transcript_text(result["segments"], timestamps=True)
    st.download_button("Download transcript", text, file_name="transcript.txt")
    st.text_area("Transcript", text, height=420, label_visibility="collapsed")


def show_chat(result):
    if not st.session_state.history:
        st.markdown('<div class="chat-intro">Ask anything about this video, or start with one of these:</div>',
                    unsafe_allow_html=True)
        for i, suggestion in enumerate(SUGGESTIONS):
            if st.button(suggestion, key=f"suggest_{i}", use_container_width=True):
                st.session_state.pending_question = suggestion
                st.rerun()

    for message in st.session_state.history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask a question about this video") or st.session_state.pending_question
    if not question:
        return
    st.session_state.pending_question = None

    try:
        with st.spinner("Thinking..."):
            answer = ask_question(result["index"], question, st.session_state.history,
                                  result["summary"])
    except Exception as error:
        st.error(f"Could not answer this question: {error}")
        return

    st.session_state.history += [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]
    st.rerun()


def show_translate(result):
    st.markdown('<div class="chat-intro">Translate the summary and subtitles into other languages.</div>',
                unsafe_allow_html=True)
    translations = result.setdefault("translations", {})
    chosen = st.pills("Languages", TARGET_LANGUAGES, selection_mode="multi",
                      label_visibility="collapsed") or []
    if len(chosen) > 3:
        st.warning("Select up to 3 languages at a time.")
        chosen = chosen[:3]

    if st.button("Translate", type="primary", use_container_width=True, disabled=not chosen):
        for lang in [l for l in chosen if l not in translations]:
            try:
                with st.spinner(f"Translating to {lang}..."):
                    translations[lang] = {
                        "summary": translate_summary(result["summary"], lang),
                        "segments": translate_segments(result["segments"], lang),
                    }
            except Exception as error:
                st.error(f"{lang} translation failed: {error}")
        st.rerun()

    for lang, data in translations.items():
        with st.expander(lang, expanded=lang in chosen):
            st.markdown(data["summary"])
            text = transcript_text(data["segments"], timestamps=True)
            st.text_area("Transcript", text, height=300, key=f"ta_{lang}",
                         label_visibility="collapsed")
            col_a, col_b = st.columns(2)
            col_a.download_button("Download subtitles (.srt)", to_srt(data["segments"]),
                                  file_name=f"subtitles_{lang.lower()}.srt", key=f"srt_{lang}",
                                  use_container_width=True)
            col_b.download_button("Download transcript (.txt)", text,
                                  file_name=f"transcript_{lang.lower()}.txt", key=f"txt_{lang}",
                                  use_container_width=True)

            st.markdown("**Dub audio**")
            gender = st.radio("Voice", ["Female", "Male"], horizontal=True,
                              key=f"voice_{lang}", label_visibility="collapsed")
            if st.button("Generate dubbed audio", key=f"dub_{lang}", use_container_width=True):
                try:
                    with st.spinner(f"Generating {lang} voice..."):
                        data["audio"] = dub(data["segments"], lang, gender)
                except Exception as error:
                    st.error(f"Dubbing failed: {error}")
            if data.get("audio"):
                st.audio(data["audio"], format="audio/mp3")
                st.download_button("Download audio (.mp3)", data["audio"],
                                   file_name=f"dub_{lang.lower()}.mp3", mime="audio/mpeg",
                                   key=f"mp3_{lang}", use_container_width=True)


def main():
    init_state()
    require_password()
    show_brand()

    result = st.session_state.result
    if result is None:
        show_landing()
        return

    show_header(result)
    tab_summary, tab_chat, tab_transcript, tab_translate = st.tabs(
        ["Summary", "Ask questions", "Transcript", "Translate"])
    with tab_summary:
        show_summary(result)
    with tab_chat:
        show_chat(result)
    with tab_transcript:
        show_transcript(result)
    with tab_translate:
        show_translate(result)


if __name__ == "__main__":
    main()
