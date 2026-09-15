"""
YouTube transcript extraction, with a two-tier fallback:
  1. youtube-transcript-api (fast, no download, usually enough)
  2. yt-dlp (pulls auto/manual captions if the API path fails)

If both fail, the caller should surface a "manual paste" option to the user
rather than a hard error — this module raises ExtractionFailed for that case.
"""

import re
import subprocess
import tempfile
import os
import glob
import json

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


class ExtractionFailed(Exception):
    pass


_YT_ID_RE = re.compile(
    r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([A-Za-z0-9_-]{11})"
)


def extract_video_id(url: str) -> str:
    match = _YT_ID_RE.search(url)
    if not match:
        # allow a bare 11-char ID too
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
            return url.strip()
        raise ExtractionFailed(f"Could not parse a YouTube video ID from: {url}")
    return match.group(1)


def _try_transcript_api(video_id: str) -> str | None:
    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(s["text"] for s in segments if s.get("text"))
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return None
    except Exception:
        return None


def _try_yt_dlp(video_id: str) -> str | None:
    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmp:
        out_tmpl = os.path.join(tmp, "%(id)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "en.*",
            "--sub-format", "vtt",
            "-o", out_tmpl,
            url,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60, check=False)
        except Exception:
            return None

        vtt_files = glob.glob(os.path.join(tmp, "*.vtt"))
        if not vtt_files:
            return None
        return _vtt_to_text(vtt_files[0])


def _vtt_to_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    text_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line:
            continue
        if line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line)  # strip inline VTT tags
        text_lines.append(line)

    # de-duplicate consecutive repeated lines (common in auto-captions)
    deduped = []
    for line in text_lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return " ".join(deduped)


def get_transcript(url_or_id: str) -> dict:
    """
    Returns {"video_id": str, "transcript": str, "source": "api"|"yt-dlp"}
    Raises ExtractionFailed if both methods fail.
    """
    video_id = extract_video_id(url_or_id)

    transcript = _try_transcript_api(video_id)
    if transcript:
        return {"video_id": video_id, "transcript": transcript, "source": "api"}

    transcript = _try_yt_dlp(video_id)
    if transcript:
        return {"video_id": video_id, "transcript": transcript, "source": "yt-dlp"}

    raise ExtractionFailed(
        "Both extraction methods failed for this video. Paste the transcript "
        "manually to still create a card."
    )
