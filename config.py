import os

from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = "openai/gpt-oss-20b"
STT_MODEL = "whisper-large-v3-turbo"
CHUNK_SECONDS = 600


def get_secret(name: str, default=None):
    """Read from environment first, then Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name, default)
    except Exception:
        return default


def max_minutes() -> int:
    try:
        return int(get_secret("MAX_MINUTES", 180))
    except (TypeError, ValueError):
        return 180
