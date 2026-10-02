from groq import Groq
from concurrent.futures import ThreadPoolExecutor
import os 
import time

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY missing")
    return Groq(api_key=api_key)


def summarize_chunk(chunk: str) -> str:
    client = get_groq_client()

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{
            "role": "user",
            "content": f"Summarize this portion of a video transcript concisely:\n\n{chunk}"
        }],
        temperature=0.3,
        max_tokens=512
    )
    return response.choices[0].message.content


def summarize(transcript: str) -> str:
    client = get_groq_client()
    
    # Split into chunks
    chunk_size = 3000
    chunks = [transcript[i:i + chunk_size] for i in range(0, len(transcript), chunk_size)]
    
    print(f"Summarizing {len(chunks)} chunks...")
    
    # Summarize chunks in parallel (order is kept)
    with ThreadPoolExecutor(max_workers=3) as executor:
        chunk_summaries = list(executor.map(summarize_chunk, chunks))
    
    # Combine summaries
    combined = "\n\n".join(chunk_summaries)
    
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{
            "role": "user",
            "content": f"""You are an expert summarizer. Combine these partial summaries 
into one final clear summary of the video in bullet points:

{combined}"""
        }],
        temperature=0.3,
        max_tokens=1024
    )
    
    return response.choices[0].message.content


def generate_title(transcript: str) -> str:
    client = get_groq_client()
    
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{
            "role": "user",
            "content": f"""Based on this video transcript, generate a short professional title 
(max 8 words). Only return the title, nothing else.

Transcript:
{transcript[:2000]}"""
        }],
        temperature=0.3,
        max_tokens=100
    )
    
    return response.choices[0].message.content
