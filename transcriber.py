from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import CHUNK_SECONDS, STT_MODEL
from llm import get_client, with_retry


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _transcribe_part(client, path: Path, offset: float, language) -> list:
    def call():
        kwargs = {"language": language} if language else {}
        return client.audio.transcriptions.create(
            file=(path.name, path.read_bytes()),
            model=STT_MODEL,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
            temperature=0.0,
            **kwargs,
        )

    result = with_retry(call)
    segments = []
    for seg in _get(result, "segments", None) or []:
        text = (_get(seg, "text", "") or "").strip()
        if text:
            segments.append({
                "start": offset + float(_get(seg, "start", 0)),
                "end": offset + float(_get(seg, "end", 0)),
                "text": text,
            })

    if not segments:
        text = (_get(result, "text", "") or "").strip()
        if text:
            segments.append({"start": offset, "end": offset, "text": text})
    return segments


def transcribe(parts: list, language=None, on_progress=None) -> list:
    """Transcribe parts in parallel; returns ordered segments with timestamps."""
    client = get_client()
    segments = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [
            pool.submit(_transcribe_part, client, p, i * CHUNK_SECONDS, language)
            for i, p in enumerate(parts)
        ]
        for done, future in enumerate(futures, start=1):
            segments.extend(future.result())
            if on_progress:
                on_progress(done, len(futures))

    return segments
