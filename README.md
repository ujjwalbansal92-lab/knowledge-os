# Knowledge OS (POC)

Turn a YouTube link into a digestible, tagged knowledge card. YouTube-only
scope for this proof of concept.

## What's here

```
backend/
  main.py         FastAPI app — routes for creating/listing cards
  extract.py       Transcript extraction: youtube-transcript-api -> yt-dlp fallback
  llm.py           Summarization/tagging — currently a MOCK, swap in Gemini later
  storage.py       SQLite persistence
  requirements.txt
frontend/
  index.html       Single-page mobile-friendly PWA
  app.js           Talks to the backend API
  style.css
  manifest.json / sw.js / icon.svg   PWA installability
render.yaml        Render.com deploy config for the backend
```

## Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then open `frontend/index.html` directly in a mobile browser (or serve it
with any static server, e.g. `python -m http.server` from inside `frontend/`).
On first load it'll ask for the backend URL — enter `http://localhost:8000`
(or your phone's LAN IP if testing on a real device, e.g. `http://192.168.x.x:8000`).

**Note:** the LLM step is mocked by default (`USE_MOCK_LLM=true`), so you can
test the whole flow — link → transcript → card → tags → filtering — for free,
with obviously-fake summaries, before spending any Gemini quota.

## Deploy the backend (free tier)

`render.yaml` is set up for [Render](https://render.com):

1. Push this repo to GitHub.
2. In Render, "New +" → "Blueprint", point it at the repo. It'll pick up
   `render.yaml` automatically.
3. Once deployed, copy the service URL (e.g. `https://knowledge-os-backend.onrender.com`)
   into the frontend's ⚙️ settings panel.

Render's free tier spins the service down after inactivity, so the first
request after idling will be slow (~30-50s cold start) — expected for a POC.

## Deploy the frontend

It's fully static — drop the `frontend/` folder on GitHub Pages, Netlify,
Vercel, or Render's static-site hosting. No build step needed.

## Wiring in the real LLM (Gemini Flash / Flash-Lite)

Everything's isolated in `backend/llm.py`:

1. `pip install google-genai` and add it to `requirements.txt`
2. Get a Gemini API key, set `GEMINI_API_KEY` as an env var
   (locally in `.env`, or in Render's dashboard — `render.yaml` already
   has a placeholder for it)
3. Set `USE_MOCK_LLM=false`
4. Replace the body of `summarize_transcript()` in `llm.py` with the real
   API call — there's a `PROMPT` constant already written and a commented-out
   example call to copy from.

## Known limitations / next steps

- **Extraction fragility**: both `youtube-transcript-api` and `yt-dlp` rely
  on YouTube's undocumented internals and can break without warning. The
  manual transcript paste is the safety net — it's wired into the same
  submit flow on the frontend, and shows automatically on a 409 response.
- **No auth / single-user**: fine for personal use; would need real auth
  before opening to ~100 users as discussed.
- **SQLite**: fine for POC; swap for Postgres before multi-user.
- **Tag-based interlinking only**: cards sharing a tag show up together via
  the filter chips — no semantic matching, by design (cheap and simple).
- **Native Android port**: once validated, wrap as a TWA like Memory Gym for
  proper share-sheet integration (share a YouTube link straight from the
  YouTube app into Knowledge OS).
