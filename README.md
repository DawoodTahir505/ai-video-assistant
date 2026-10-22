# ▶ AI Video Assistant

**Understand any video in minutes.** Paste a YouTube link or upload a file, get a clear summary, then ask questions about it in plain language.

## Features

- **Summary:** title, overview, key points and takeaways
- **Ask questions:** answers cite exact timestamps like `[12:34]`
- **Transcript:** full timestamped text, ready to download
- **Translate:** summary and subtitles (`.srt`) in 12 languages
- **Dub:** translated voice-over audio (`.mp3`), male or female voice

## How it works

```
Link / File → yt-dlp + ffmpeg → Whisper (Groq) → gpt-oss summary
                                      ↓
                        BM25 search over transcript → timestamped answers
```

Long media is split into 10-minute chunks and transcribed in parallel. Questions use BM25 retrieval, so only the relevant parts of the transcript are sent to the model.

## Run locally

```bash
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key" > .env
streamlit run app.py
```

Get a free key at [console.groq.com](https://console.groq.com). ffmpeg must be installed (or it is picked up via `static-ffmpeg`).

## Deploy free

**Streamlit Community Cloud:** push to GitHub, create the app at [share.streamlit.io](https://share.streamlit.io) with `app.py` as the main file, and add this under Secrets:

```toml
GROQ_API_KEY = "your_key"
```

`packages.txt` installs ffmpeg automatically.

**Docker:**

```bash
docker build -t ai-video-assistant .
docker run -p 8501:8501 -e GROQ_API_KEY=your_key ai-video-assistant
```

## Good to know

- YouTube blocks most cloud servers. If links fail, add `YT_COOKIES` (Netscape `cookies.txt` contents) as a secret, or use **Upload file**.
- Dubbing uses Microsoft Edge neural voices (`edge-tts`, no key needed). It is not time-synced to the video.
- `MAX_MINUTES` limits media length (default 180).

## Tech stack

Python · Streamlit · Groq (Whisper large-v3-turbo, gpt-oss-20b) · yt-dlp · ffmpeg · edge-tts
