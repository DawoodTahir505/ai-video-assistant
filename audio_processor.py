import subprocess
from pathlib import Path
from urllib.parse import urlparse
import requests

from config import CHUNK_SECONDS, max_minutes

def validate_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Enter a valid http(s) video link.")
    return url

def download_audio(url: str, workdir: Path) -> Path:
    url = validate_url(url)
    
    # Using an external public extractor API to bypass cloud datacenter IP blocks
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "isAudioOnly": True,
        "downloadMode": "audio"
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        data = response.json()
        
        # Check if the API successfully returned a download link
        if data.get("status") in ("redirect", "stream", "picker"):
            download_url = data.get("url")
            if not download_url and data.get("picker"):
                # If it's a picker response, take the first available audio/media link
                download_url = data["picker"][0].get("url")
                
            if not download_url:
                raise RuntimeError("Could not retrieve download stream from API.")
                
            # Download the audio file using requests stream
            audio_response = requests.get(download_url, stream=True, timeout=60)
            audio_response.raise_for_status()
            
            output_path = workdir / "source.mp3"
            with open(output_path, "wb") as f:
                for chunk in audio_response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return output_path
        else:
            error_msg = data.get("text", "Unknown external extractor error.")
            raise RuntimeError(f"Extraction failed: {error_msg}")

    except Exception as error:
        raise RuntimeError(
            f"YouTube link processing failed: {str(error)}. "
            "Please try another link or use the 'Upload file' tab."
        ) from error

def probe_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except Exception:
        return 0.0

def prepare_audio(src: Path, out_dir: Path) -> list:
    """Convert to mono 16 kHz 32 kbps MP3 and split into fixed-length parts."""
    if probe_duration(src) > max_minutes() * 60:
        raise ValueError(f"Media is longer than {max_minutes()} minutes.")

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(src), "-vn", "-map", "0:a:0",
        "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "32k",
        "-f", "segment", "-segment_time", str(CHUNK_SECONDS),
        "-reset_timestamps", "1", str(out_dir / "part_%04d.mp3"),
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as error:
        tail = error.stderr.decode(errors="ignore")[-200:]
        raise RuntimeError(f"Could not read audio from this file. {tail}") from error

    parts = sorted(out_dir.glob("part_*.mp3"))
    if not parts:
        raise RuntimeError("No audio track found.")
    return parts
