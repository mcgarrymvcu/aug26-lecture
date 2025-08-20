# INFO 300 — TCP/IP Lecture (Option C)

This Streamlit app delivers your slide deck with narration text and an OpenAI-powered Q&A chat. 
Recommended deployment: **Streamlit Community Cloud** (students only need a link).

## Files
- `app.py` — Streamlit app
- `narration.json` — per-slide narration (slides 02–26)
- `slides/slide_02.png … slide_26.png` — export from PowerPoint (replace placeholders)
- `videos/intro.mp4` — optional 1–2 minute personal intro recorded in Zoom/Loom (optional)
- `requirements.txt` — Python deps

## How to Export Slides
In PowerPoint: **File → Export → PNG → “All Slides”**.  
Rename to `slide_02.png` … `slide_26.png` and place in the `slides/` folder.

## Streamlit Community Cloud Deploy
1. Push this folder to a GitHub repo.
2. Deploy via https://streamlit.io/
3. In **App → Settings → Secrets**, add:
```
OPENAI_API_KEY = "sk-..."
```
4. Click **Deploy**; share the app URL on Canvas.

## Optional: Short Real Intro
Record a 60–120s video (Zoom/Loom) explaining you’re on jury duty and how to use the app. 
Save as `videos/intro.mp4` (or host externally and paste the URL in `app.py`).

