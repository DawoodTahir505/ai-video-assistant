import os
import shutil
import tempfile
import static_ffmpeg
from groq import Groq
from pydub import AudioSegment
from dotenv import load_dotenv
load_dotenv()

static_ffmpeg.add_paths()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MAX_FILE_MB = 24
CHUNK_MINUTES = 10


def split_audio(audio_path: str):
    """Split big audio into small compressed parts (Groq limit is 25 MB)."""
    if os.path.getsize(audio_path) <= MAX_FILE_MB * 1024 * 1024:
        return [audio_path], None

    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_channels(1).set_frame_rate(16000)

    temp_dir = tempfile.mkdtemp(prefix="AUDIO_PARTS_")
    step = CHUNK_MINUTES * 60 * 1000
    parts = []

    for i, start in enumerate(range(0, len(audio), step)):
        part_path = os.path.join(temp_dir, f"part_{i}.mp3")
        audio[start:start + step].export(part_path, format="mp3", bitrate="64k")
        parts.append(part_path)

    return parts, temp_dir


def transcribe_chunk_groq(chunk_path: str) -> str:
    """Transcribe audio using Groq's cloud whisper-large-v3 model."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing from environment / .env")

    client = Groq(api_key=GROQ_API_KEY)

    with open(chunk_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(chunk_path), file.read()),
            model="whisper-large-v3",
            language="en",
            temperature=0.0
        )

    return getattr(transcription, "text", str(transcription))


def transcribe_all(chunks: list) -> str:
    """Transcribe all chunks sequentially via Groq API."""
    full_transcript = ""
    print(f"Using Groq Cloud API (whisper-large-v3) for transcription.")

    for i, chunk in enumerate(chunks):
        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")
        parts, temp_dir = split_audio(chunk)

        try:
            for j, part in enumerate(parts):
                if len(parts) > 1:
                    print(f"  Part {j + 1}/{len(parts)}...")
                text = transcribe_chunk_groq(part)
                full_transcript += text + " "
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

    print("Transcription complete.")
    return full_transcript.strip()
