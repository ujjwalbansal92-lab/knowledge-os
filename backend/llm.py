"""
LLM interface for Knowledge OS.

Right now this returns a MOCK response so the rest of the pipeline can be
built and tested without an API key or spending any quota.

To wire in real Gemini Flash / Flash-Lite later:
1. `pip install google-genai` (add to requirements.txt)
2. Set GEMINI_API_KEY in your environment (.env file, or Render's env vars)
3. Replace the body of `summarize_transcript()` below with a real call,
   keeping the same return shape: {"title": str, "summary": str, "tags": [str, ...]}
   The PROMPT constant below is written so you can paste it straight into
   a Gemini call's system/user message once you switch over.
"""

import os
import re
import hashlib

USE_MOCK = os.getenv("USE_MOCK_LLM", "true").lower() != "false"

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


def summarize_transcript(transcript: str, video_title: str | None = None) -> dict:
    """
    Returns {"title": str, "summary": str, "tags": [str, ...]}
    """
    if USE_MOCK:
        return _mock_response(transcript, video_title)

    # --- Real Gemini call goes here when you're ready ---
    # from google import genai
    # client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    # resp = client.models.generate_content(
    #     model="gemini-2.0-flash-lite",
    #     contents=PROMPT.format(transcript=transcript[:15000]),
    # )
    # import json
    # return json.loads(resp.text)
    raise NotImplementedError(
        "USE_MOCK_LLM is false but no real LLM call is implemented yet. "
        "See the comment block in llm.py."
    )
