import re
from concurrent.futures import ThreadPoolExecutor

from llm import chat

CHUNK_CHARS = 9000
DIRECT_LIMIT = 24000

FINAL_PROMPT = """Summarize this video in Markdown using exactly this structure:

## Overview
2-3 sentences.

## Key points
- 5 to 8 concise bullets.

## Takeaways
- 2 to 4 bullets.

Use the same language as the source. Do not add information not present.

{text}"""


def _split(text: str, size: int) -> list:
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(" ", start, end)
            end = cut if cut > start else end
        chunks.append(text[start:end])
        start = end
    return chunks


def _partial(chunk: str) -> str:
    return chat([{
        "role": "user",
        "content": f"Summarize this part of a video transcript in detail, as bullets:\n\n{chunk}",
    }], max_tokens=1024)


def summarize(transcript: str) -> str:
    if len(transcript) <= DIRECT_LIMIT:
        source = transcript
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            source = "\n\n".join(pool.map(_partial, _split(transcript, CHUNK_CHARS)))
    return chat([{"role": "user", "content": FINAL_PROMPT.format(text=source)}], max_tokens=2048)


def generate_title(transcript: str) -> str:
    title = chat([{
        "role": "user",
        "content": "Write a short professional title (max 8 words) for this video. "
                   f"Return only the title.\n\n{transcript[:2000]}",
    }], max_tokens=200)
    return re.sub(r'^[\s"\'*#]+|[\s"\'*#]+$', "", title.splitlines()[0]) if title else "Video analysis"
