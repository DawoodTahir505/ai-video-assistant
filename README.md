# AI Video Assistant

Summarize and chat with any video/audio. Streamlit + Groq (Whisper + gpt-oss).

## Run locally
    pip install -r requirements.txt
    cp .env.example .env   # set GROQ_API_KEY
    streamlit run app.py

## Deploy: Streamlit Community Cloud
1. Push to GitHub (`.env` is ignored).
2. share.streamlit.io → New app → select repo, main file `app.py`.
3. Advanced settings → Secrets:
       GROQ_API_KEY = "..."
       APP_PASSWORD = "..."   # optional access gate
4. Deploy. `packages.txt` installs ffmpeg automatically.

## Deploy: Docker (Render / Railway / Fly.io / VPS)
    docker build -t ai-video-assistant .
    docker run -p 8501:8501 -e GROQ_API_KEY=... ai-video-assistant
Set `GROQ_API_KEY` (and optionally `APP_PASSWORD`) as environment variables on the host.

## Notes
- YouTube often blocks datacenter IPs. If link downloads fail, supply `YT_COOKIES` (Netscape cookie file contents) or use file upload.
- Translate tab: summary + subtitles (.srt) in up to 3 languages at a time.
- Dubbing uses Microsoft Edge neural voices via `edge-tts` (no API key). It is a voice-over of the translated text, not time-synced to the original video.
- `MAX_MINUTES` caps media length (default 180).
