import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts

MAX_CHARS = 2500

VOICES = {
    "Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
    "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"},
    "Arabic": {"Female": "ar-SA-ZariyahNeural", "Male": "ar-SA-HamedNeural"},
    "Bengali": {"Female": "bn-BD-NabanitaNeural", "Male": "bn-BD-PradeepNeural"},
    "Spanish": {"Female": "es-ES-ElviraNeural", "Male": "es-ES-AlvaroNeural"},
    "French": {"Female": "fr-FR-DeniseNeural", "Male": "fr-FR-HenriNeural"},
    "German": {"Female": "de-DE-KatjaNeural", "Male": "de-DE-ConradNeural"},
    "Portuguese": {"Female": "pt-BR-FranciscaNeural", "Male": "pt-BR-AntonioNeural"},
    "Turkish": {"Female": "tr-TR-EmelNeural", "Male": "tr-TR-AhmetNeural"},
    "Russian": {"Female": "ru-RU-SvetlanaNeural", "Male": "ru-RU-DmitryNeural"},
    "Chinese": {"Female": "zh-CN-XiaoxiaoNeural", "Male": "zh-CN-YunxiNeural"},
    "Japanese": {"Female": "ja-JP-NanamiNeural", "Male": "ja-JP-KeitaNeural"},
}


def _chunks(segments: list) -> list:
    chunks, buf, size = [], [], 0
    for seg in segments:
        buf.append(seg["text"])
        size += len(seg["text"])
        if size >= MAX_CHARS:
            chunks.append(" ".join(buf))
            buf, size = [], 0
    if buf:
        chunks.append(" ".join(buf))
    return chunks


async def _synth(text: str, voice: str, path: Path, gate: asyncio.Semaphore):
    async with gate:
        for attempt in range(3):
            try:
                await edge_tts.Communicate(text, voice).save(str(path))
                return
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(2)


async def _run(texts: list, voice: str, folder: Path) -> list:
    gate = asyncio.Semaphore(3)
    paths = [folder / f"part_{i:04d}.mp3" for i in range(len(texts))]
    await asyncio.gather(*[_synth(t, voice, p, gate) for t, p in zip(texts, paths)])
    return paths


def dub(segments: list, language: str, gender: str = "Female") -> bytes:
    """Synthesize translated segments into a single MP3 voice-over."""
    voice = VOICES[language][gender]
    texts = _chunks(segments)
    if not texts:
        raise RuntimeError("Nothing to dub.")

    with tempfile.TemporaryDirectory(prefix="dub_") as tmp:
        folder = Path(tmp)
        paths = asyncio.run(_run(texts, voice, folder))

        listing = folder / "list.txt"
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in paths))
        out = folder / "dubbed.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
             "-c:a", "libmp3lame", "-b:a", "64k", str(out)],
            capture_output=True, check=True,
        )
        return out.read_bytes()
