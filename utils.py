def fmt_time(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def transcript_text(segments: list, timestamps: bool = False) -> str:
    if timestamps:
        return "\n".join(f"[{fmt_time(s['start'])}] {s['text']}" for s in segments)
    return " ".join(s["text"] for s in segments)
