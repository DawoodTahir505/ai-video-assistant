import re
from concurrent.futures import ThreadPoolExecutor

from llm import chat

BATCH = 40
_LINE = re.compile(r"^\s*(\d+)\s*\|\s*(.+)$")

LANGUAGES = [
    "Urdu", "Hindi", "Arabic", "Bengali", "Spanish", "French", "German",
    "Portuguese", "Turkish", "Russian", "Chinese", "Japanese",
]

_SYSTEM = (
    "You are a professional subtitle translator. Translate each numbered line into {lang}. "
    "Keep the same numbering and return exactly one line per input in the format N|translation. "
    "Do not merge, skip, or add lines. Output nothing else."
)


def _translate_batch(batch: list, language: str) -> list:
    numbered = "\n".join(f"{i}|{s['text']}" for i, s in enumerate(batch, 1))
    output = chat(
        [{"role": "system", "content": _SYSTEM.format(lang=language)},
         {"role": "user", "content": numbered}],
        max_tokens=4096, temperature=0.2,
    )
    found = {}
    for line in output.splitlines():
        match = _LINE.match(line)
        if match:
            found[int(match.group(1))] = match.group(2).strip()
    return [{**s, "text": found.get(i, s["text"])} for i, s in enumerate(batch, 1)]


def translate_segments(segments: list, language: str) -> list:
    batches = [segments[i:i + BATCH] for i in range(0, len(segments), BATCH)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = pool.map(lambda b: _translate_batch(b, language), batches)
    return [seg for batch in results for seg in batch]


def translate_summary(summary: str, language: str) -> str:
    return chat([{
        "role": "user",
        "content": f"Translate this Markdown into {language}. Keep the Markdown structure. "
                   f"Return only the translation.\n\n{summary}",
    }], max_tokens=2048, temperature=0.2)


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(segments: list) -> str:
    blocks = []
    for i, seg in enumerate(segments, 1):
        end = seg["end"] if seg["end"] > seg["start"] else seg["start"] + 2
        blocks.append(f"{i}\n{_srt_time(seg['start'])} --> {_srt_time(end)}\n{seg['text']}\n")
    return "\n".join(blocks)
