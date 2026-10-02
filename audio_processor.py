import yt_dlp
import os
import time
import uuid
import static_ffmpeg

static_ffmpeg.add_paths()

def download_youtube_audio(url: str) -> str:
    """Download YouTube audio as MP3 with retries."""

    file_id = f"downloaded_audio_{uuid.uuid4().hex[:8]}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': file_id,
        'socket_timeout': 30,
    }

    for attempt in range(2):
        try:
            print(f"Download attempt {attempt + 1}/2...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            audio_path = f"{file_id}.mp3"
            if os.path.exists(audio_path):
                return audio_path
                
        except Exception as e:
            if attempt < 1:
                print(f"Retrying in 5s...")
                time.sleep(5)
            else:
                raise Exception(f"YouTube download failed: {str(e)[:100]}")

    raise Exception("YouTube download failed after retries")
