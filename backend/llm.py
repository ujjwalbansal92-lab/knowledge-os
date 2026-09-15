"""
LLM interface for Knowledge OS.

Uses Gemini Flash-Lite to summarize and tag transcripts. Set USE_MOCK_LLM=false
and GEMINI_API_KEY in the environment to use the real model; otherwise this
falls back to a deterministic mock so the pipeline can be tested for free.
"""

import os
import re
import json
import hashlib

USE_MOCK = os.getenv("USE_MOCK_LLM", "true").lower() != "false"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
PROMPT = """You are helping build a personal knowledge base from YouTube video transcripts.
Given the transcript below, respond with STRICT JSON only, no markdown fences, no preamble:

{{
  "title": "<a short, specific title for this knowledge card, max 8 words>",
  "summary": "<a digestible summary in 3-6 sentences, written so it's useful on its own, without needing to rewatch the video>",
  "tags": ["<2 to 5 short lowercase tags, e.g. 'psychology', 'new vocabulary', 'geography'>"]
}}

Transcript:
{transcript}
"""

# A small fixed vocabulary the mock uses to fake plausible tags deterministically,
# so repeated tests on the same video give repeatable (fake) results.
_MOCK_TAG_POOL = [
    "psychology", "new vocabulary", "geography", "history", "science",
    "productivity", "finance", "technology", "health", "philosophy",
]

def _mock_response(transcript: str, video_title: str | None) -> dict:
    words = re.findall(r"[A-Za-z']{5,}", transcript)
    seed = int(hashlib.sha1(transcript.encode("utf-8", "ignore")).hexdigest(), 16)
    tags = []
    pool = _MOCK_TAG_POOL[:]
    for i in range(2):
        idx = (seed >> (i * 8)) % len(pool)
        tag = pool.pop(idx)
        tags.append(tag)

    snippet = " ".join(transcript.split()[:60])
    title = video_title or (" ".join(words[:6]).title() or "Untitled Knowledge Card")

    return {
        "title": title[:80],
        "summary": (
            f"[MOCK SUMMARY — no LLM call made] This card was generated from a "
            f"transcript of about {len(transcript.split())} words. Opening context: "
            f'"{snippet}...". Replace llm.py:summarize_transcript with a real Gemini '
            f"call to get an actual summary."
        ),
        "tags": tags,
    }

def _clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return text

def _real_response(transcript: str, video_title: str | None) -> dict:
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=PROMPT.format(transcript=transcript[:15000]),
    )
    data = json.loads(_clean_json_text(resp.text))

    return {
        "title": str(data.get("title") or video_title or "Untitled Knowledge Card")[:80],
        "summary": str(data.get("summary", "")),
        "tags": [str(t).lower() for t in data.get("tags", [])][:5],
    }

def summarize_transcript(transcript: str, video_title: str | None = None) -> dict:
    """
    Returns {"title": str, "summary": str, "tags": [str, ...]}
    """
    if USE_MOCK:
        return _mock_response(transcript, video_title)

    return _real_response(transcript, video_title)
