from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import extract
import llm
import storage

storage.init_db()

app = FastAPI(title="Knowledge OS API")

# Wide-open CORS for the POC. Tighten this to your actual frontend origin
# once you deploy (see README).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LinkSubmission(BaseModel):
    url: str


class ManualSubmission(BaseModel):
    url: str | None = None
    transcript: str
    title: str | None = None


def _build_card_response(video_id, source_url, extraction_source, transcript, seed_title=None):
    result = llm.summarize_transcript(transcript, video_title=seed_title)
    card_id = storage.save_card(
        video_id=video_id,
        source_url=source_url,
        title=result["title"],
        summary=result["summary"],
        tags=result["tags"],
        extraction_source=extraction_source,
    )
    return storage.get_card(card_id)


@app.post("/api/cards")
def create_card_from_link(payload: LinkSubmission):
    """
    Primary flow: user shares a YouTube URL.
    Tries youtube-transcript-api, then yt-dlp. On total failure, returns a
    409 with needs_manual=true so the frontend can show the paste fallback.
    """
    try:
        extraction = extract.get_transcript(payload.url)
    except extract.ExtractionFailed as e:
        raise HTTPException(
            status_code=409,
            detail={"message": str(e), "needs_manual": True},
        )

    card = _build_card_response(
        video_id=extraction["video_id"],
        source_url=payload.url,
        extraction_source=extraction["source"],
        transcript=extraction["transcript"],
    )
    return card


@app.post("/api/cards/manual")
def create_card_from_manual_paste(payload: ManualSubmission):
    """
    Fallback flow: user pastes a transcript directly (either because
    extraction failed, or by choice).
    """
    video_id = None
    if payload.url:
        try:
            video_id = extract.extract_video_id(payload.url)
        except extract.ExtractionFailed:
            video_id = None

    card = _build_card_response(
        video_id=video_id,
        source_url=payload.url,
        extraction_source="manual",
        transcript=payload.transcript,
        seed_title=payload.title,
    )
    return card


@app.get("/api/cards")
def get_cards(tag: str | None = None):
    return storage.list_cards(tag=tag)


@app.get("/api/cards/{card_id}")
def get_card(card_id: int):
    card = storage.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.get("/api/tags")
def get_tags():
    return [{"tag": t, "count": c} for t, c in storage.all_tags()]


@app.get("/api/health")
def health():
    return {"status": "ok", "mock_llm": llm.USE_MOCK}
