import subprocess
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

from config import CHUNK_SECONDS, get_secret, max_minutes

try:
    import static_ffmpeg

    static_ffmpeg.add_paths()
except Exception:
    pass  # fall back to ffmpeg on PATH


def validate_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Enter a valid http(s) video link.")
    return url


def download_audio(url: str, workdir: Path) -> Path:
    url = validate_url(url)
    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(workdir / "source.%(ext)s"),
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 3,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        }
    }

    cookies = get_secret("YT_COOKIES")
    if cookies:
        cookie_file = workdir / "cookies.txt"
        cookie_file.write_text(cookies)
        opts["cookiefile"] = str(cookie_file)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if (info.get("duration") or 0) > max_minutes() * 60:
                raise ValueError(f"Video is longer than {max_minutes()} minutes.")
            ydl.download([url])
    except Exception as error:
        # Graceful handling for YouTube cloud server IP blocks (403 Forbidden)
        raise RuntimeError(
            "YouTube blocks direct links from cloud servers (403 Forbidden). "
            "Please switch to the **'Upload file'** tab above and upload your audio/video file directly to use the app for free with zero errors!"
        ) from error

    files = [p for p in workdir.glob("source.*")]
    if not files:
        raise RuntimeError("Download failed: no file produced.")
    return files[0]


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
