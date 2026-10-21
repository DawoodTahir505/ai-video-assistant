import math
import re
from collections import Counter
from dataclasses import dataclass

from llm import chat
from utils import fmt_time

K1, B = 1.5, 0.75
FULL_CONTEXT_CHARS = 12000

_TOKEN = re.compile(r"\w+", re.UNICODE)
_STOP = set(
    "the a an and or but of to in on at for with by from is are was were be been this that "
    "these those it its as what who whom which when where why how do does did can could "
    "about video say says said tell me please".split()
)


def _tokens(text: str) -> list:
    return [w for w in _TOKEN.findall(text.lower()) if len(w) > 1 and w not in _STOP]


@dataclass
class Chunk:
    start: float
    text: str


def _make_chunks(segments: list, max_chars: int) -> list:
    chunks, buf, size = [], [], 0
    for seg in segments:
        buf.append(seg)
        size += len(seg["text"])
        if size >= max_chars:
            chunks.append(Chunk(buf[0]["start"], " ".join(s["text"] for s in buf)))
            buf, size = [seg], len(seg["text"])  # one-segment overlap
    if buf and (not chunks or len(buf) > 1):
        chunks.append(Chunk(buf[0]["start"], " ".join(s["text"] for s in buf)))
    return chunks


class TranscriptIndex:
    """BM25 index over timestamped transcript chunks."""

    def __init__(self, segments: list, max_chars: int = 700):
        self.chunks = _make_chunks(segments, max_chars)
        self._tf = [Counter(_tokens(c.text)) for c in self.chunks]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = (sum(self._len) / len(self._len)) if self._len else 1
        self._df = Counter()
        for tf in self._tf:
            self._df.update(tf.keys())
        self.total_chars = sum(len(c.text) for c in self.chunks)

    def search(self, query: str, k: int = 6) -> list:
        n = len(self.chunks)
        if n <= k:
            return list(self.chunks)

        terms = set(_tokens(query))
        scored = []
        for i, tf in enumerate(self._tf):
            score = 0.0
            for w in terms:
                f = tf.get(w, 0)
                if not f:
                    continue
                idf = math.log(1 + (n - self._df[w] + 0.5) / (self._df[w] + 0.5))
                norm = f + K1 * (1 - B + B * self._len[i] / (self._avg or 1))
                score += idf * f * (K1 + 1) / norm
            scored.append((score, i))

        ranked = sorted(scored, key=lambda x: -x[0])[:k]
        if ranked[0][0] == 0:  # broad question: spread across the video
            picks = {int(j * n / k) for j in range(k)}
        else:
            picks = {i for s, i in ranked if s > 0}
        return [self.chunks[i] for i in sorted(picks)]


SYSTEM = (
    "You answer questions about a video using only the provided transcript excerpts. "
    "Be clear and concise. Cite moments with their timestamps in the form [mm:ss]. "
    "If the answer is not in the transcript, reply exactly: Not found in transcript."
)


def ask_question(index: TranscriptIndex, question: str, history=None, summary: str = "") -> str:
    history = history or []

    query = question
    if len(question.split()) < 5:  # short follow-up: add prior user question for context
        prior = [m["content"] for m in history if m["role"] == "user"]
        if prior:
            query = f"{prior[-1]} {question}"

    chunks = index.chunks if index.total_chars <= FULL_CONTEXT_CHARS else index.search(query)
    context = "\n\n".join(f"[{fmt_time(c.start)}] {c.text}" for c in chunks)

    messages = [{"role": "system", "content": SYSTEM}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history[-6:]]
    overview = f"Video overview:\n{summary}\n\n" if summary else ""
    messages.append({
        "role": "user",
        "content": f"{overview}Transcript excerpts:\n{context}\n\nQuestion: {question}",
    })
    return chat(messages, max_tokens=1024, temperature=0.2)
