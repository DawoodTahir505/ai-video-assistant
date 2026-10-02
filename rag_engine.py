import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MODEL = "openai/gpt-oss-20b"


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY missing")
    return Groq(api_key=api_key)


def build_rag_chain(transcript: str):
    return transcript


def get_relevant_parts(transcript: str, question: str, top_k: int = 5) -> str:
    """Return the transcript parts most related to the question."""

    # Short transcript - send everything
    if len(transcript) <= 6000:
        return transcript

    # Split into chunks of 5 sentences
    sentences = [s.strip() for s in transcript.split(".") if s.strip()]
    chunks = [". ".join(sentences[i:i + 5]) + "." for i in range(0, len(sentences), 5)]

    keywords = [w for w in question.lower().split() if len(w) > 3]

    scores = []
    for i, chunk in enumerate(chunks):
        score = sum(1 for kw in keywords if kw in chunk.lower())
        scores.append((score, i))

    best = sorted(scores, reverse=True)[:top_k]

    # No keyword match (general question) - spread chunks across the transcript
    if best[0][0] == 0:
        step = max(1, len(chunks) // top_k)
        best = [(0, i) for i in range(0, len(chunks), step)][:top_k]

    # Keep original order
    indexes = sorted(i for _, i in best)
    return "\n\n".join(chunks[i] for i in indexes)


def ask_question(transcript: str, question: str, history: list = None) -> str:
    client = get_groq_client()

    context = get_relevant_parts(transcript, question)

    messages = [
        {
            "role": "system",
            "content": (
                "You answer questions about a video using only its transcript. "
                "Give a clear, short answer in your own words. "
                "If the answer is not in the transcript, say: Not found in transcript."
            ),
        }
    ]

    # Last few messages for follow-up questions
    for message in (history or [])[-6:]:
        messages.append({"role": message["role"], "content": message["content"]})

    messages.append({
        "role": "user",
        "content": f"Transcript:\n{context}\n\nQuestion: {question}"
    })

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=1024
    )

    return response.choices[0].message.content
