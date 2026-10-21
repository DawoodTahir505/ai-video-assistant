import time
from functools import lru_cache

from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

from config import LLM_MODEL, get_secret


@lru_cache(maxsize=1)
def get_client() -> Groq:
    key = get_secret("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    return Groq(api_key=key)


def with_retry(fn, tries: int = 4):
    for attempt in range(tries):
        try:
            return fn()
        except (RateLimitError, APIConnectionError):
            if attempt == tries - 1:
                raise
        except APIStatusError as error:
            if error.status_code < 500 or attempt == tries - 1:
                raise
        time.sleep(2 ** attempt * 2)


def chat(messages: list, max_tokens: int = 2048, temperature: float = 0.3) -> str:
    client = get_client()

    def call():
        return client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body={"reasoning_effort": "low"},
        )

    response = with_retry(call)
    return (response.choices[0].message.content or "").strip()
