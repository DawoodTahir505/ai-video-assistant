# AI Video Assistant

Turn any video or audio file into a clear summary, then ask questions about it in plain language.

## Features

- Accepts a YouTube link or an uploaded video/audio file
- Transcribes speech to text (Groq Whisper large-v3)
- Generates a title and a bullet-point summary
- Answers questions about the content, with follow-up support
- Handles long files by compressing and splitting audio automatically

## Tech Stack

- Python
- Streamlit (interface)
- Groq API: `whisper-large-v3` (transcription), `openai/gpt-oss-20b` (summary and answers)
- yt-dlp and static-ffmpeg (YouTube download and audio processing)
- pydub (audio splitting)

## Project Structure

```
app.py              Streamlit interface
audio_processor.py  YouTube audio download
transcriber.py      Speech-to-text, splits large audio
summarizer.py       Title and summary
rag_engine.py       Question answering over the transcript
main.py             Command-line version (optional)
requirements.txt    Python dependencies
packages.txt        System packages for deployment (ffmpeg)
```

## Setup

1. Clone the repository and open the folder.

2. Create and activate a virtual environment:

   ```
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS / Linux
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project folder:

   ```
   GROQ_API_KEY=your_key_here
   ```

   Get a key at https://console.groq.com.

## Run

```
streamlit run app.py
```

Command-line version:

```
python main.py
```

## Usage

1. Paste a YouTube link or upload a video/audio file.
2. Select **Analyze video** and wait for processing.
3. Read the summary in the **Summary** tab.
4. Ask questions in the **Ask questions** tab.

## Deploy on Streamlit Cloud

1. Push the project to GitHub (do not commit `.env`).
2. Go to https://share.streamlit.io and select **Create app**.
3. Choose the repository and set the main file to `app.py`.
4. In **Advanced settings → Secrets**, add:

   ```
   GROQ_API_KEY = "your_key_here"
   ```

5. Select **Deploy**.

`packages.txt` must contain `ffmpeg`, and the dependency file must be named `requirements.txt` (lowercase).

## Limitations

- YouTube downloads are often blocked on cloud servers. Use file upload on hosted deployments.
- Transcription is set to English.
- Answers are based on the transcript only, with no timestamps.
- Groq API rate limits apply on the free tier.

## Environment Variables

| Name | Description |
|------|-------------|
| `GROQ_API_KEY` | Groq API key used for transcription, summary and answers |
