import os, glob, json, itertools, re
import streamlit as st
from openai import OpenAI

# ---------- Page config ----------
st.set_page_config(page_title="INFO 300 — TCP/IP Lecture", layout="wide")

# ---------- Load narration ----------
with open("narration.json", "r", encoding="utf-8") as f:
    NARR = json.load(f)  # expects keys "02"..."26"

# ---------- Find slides (flexible + natural numeric sort) ----------
patterns = [
    "slides/slide_*.png", "slides/slide_*.PNG",
    "slides/Slide*.png",  "slides/Slide*.PNG",
    "slides/*.png",       "slides/*.PNG",
]
all_files = set(itertools.chain.from_iterable(glob.glob(p) for p in patterns))

def extract_slide_number(path: str) -> int:
    """Pull first number from filename. If none, sort it last."""
    m = re.search(r"(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else 9999

# Natural numeric sort: Slide1, Slide2, ... Slide10
slide_imgs = sorted(all_files, key=extract_slide_number)

def to_two_digit_slide_num(path: str, idx: int) -> str:
    """Return slide number as 2 digits for narration keys (e.g., '02')."""
    n = extract_slide_number(path)
    return f"{n:02d}" if n != 9999 else f"{idx + 2:02d}"  # fallback assumes deck starts at slide 2

# ---------- Session state ----------
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are Professor McGarry teaching INFO 300 (IT Infrastructure). "
                "You are lecturing on the TCP/IP model using a FIVE-layer view: "
                "Application (5), Transport (4), Network (3), Data Link (2), Physical (1). "
                "Answer only in-scope questions (TCP/IP foundations, packetization, circuit vs packet, "
                "basic tools like ipconfig/ping/nslookup). Be concise, practical, and clear. "
                "If asked about unrelated topics, say it’s out of scope for today’s lecture."
            ),
        }
    ]
if "tts_cache" not in st.session_state:
    st.session_state.tts_cache = {}  # key: slide_num -> bytes

# ---------- OpenAI client from Secrets ----------
def get_openai_client():
    key = st.secrets.get("OPENAI_API_KEY", "")
    if not key:
        # Show the warning in the right column as well, but keep sidebar quiet
        return None
    try:
        return OpenAI(api_key=key)
    except Exception:
        return None

client = get_openai_client()

# ---------- Layout ----------
left, right = st.columns([2, 1])

# ===== LEFT: Slides, narration, audio =====
with left:
    st.title("INFO 300 — TCP/IP Model (5-layer)")

    # Intro video (local or URL from Secrets)
    intro_video_path = "videos/intro.mp4"
    intro_video_url = st.secrets.get("INTRO_VIDEO_URL", "").strip()
    if os.path.exists(intro_video_path) or intro_video_url:
        with st.expander("Play instructor intro (1–2 min)", expanded=False):
            st.video(intro_video_path if os.path.exists(intro_video_path) else intro_video_url)

    # Slide panel
    if not slide_imgs:
        st.warning("No slides found. Please place PNGs in the 'slides/' folder at the repo root.")
    else:
        cur = slide_imgs[st.session_state.idx]
        slide_num = to_two_digit_slide_num(cur, st.session_state.idx)

        st.markdown(f"### Slide {slide_num}")
        st.image(cur, use_container_width=True)

        st.markdown("#### Narration")
        narration_text = NARR.get(slide_num, "No narration found for this slide.")
        st.write(narration_text)

        # Audio narration (on-demand TTS)
        t1, t2, _ = st.columns([1, 1, 3])
        if t1.button("▶️ Play audio narration", key=f"tts_{slide_num}", use_container_width=True):
            if client is None:
                st.warning("OpenAI key missing or invalid — cannot synthesize audio.")
            else:
                if slide_num not in st.session_state.tts_cache:
                    try:
                        # OpenAI TTS (no 'format' arg; defaults to MP3)
                        speech = client.audio.speech.create(
                            model="gpt-4o-mini-tts",
                            voice="alloy",
                            input=narration_text,
                        )
                        audio_bytes = speech.content  # bytes in recent SDKs
                        st.session_state.tts_cache[slide_num] = audio_bytes
                    except Exception as e:
                        st.error(f"Audio synthesis failed: {e}")
                if slide_num in st.session_state.tts_cache and st.session_state.tts_cache[slide_num]:
                    st.audio(st.session_state.tts_cache[slide_num], format="audio/mp3")
        if t2.button("⟲ Regenerate audio", key=f"tts_regen_{slide_num}", use_container_width=True) and client:
            st.session_state.tts_cache.pop(slide_num, None)
            st.rerun()

        # Prev / Next
        c1, _, c3 = st.columns([1, 1, 1])
        if c1.button("⏮ Prev", use_container_width=True) and st.session_state.idx > 0:
            st.session_state.idx -= 1
            st.rerun()
        if c3.button("Next ⏭", use_container_width=True) and st.session_state.idx < len(slide_imgs) - 1:
            st.session_state.idx += 1
            st.rerun()

# ===== RIGHT: Avatar (above Q&A) + Q&A =====
with right:
    # Headshot ABOVE Q&A — shown once, here only.
    # Looks in slides/avatar.jpg first (since you said it's with slides), then repo root.
    avatar_path = None
    for cand in ("slides/avatar.jpg", "slides/avatar.png", "avatar.jpg", "avatar.png"):
        if os.path.exists(cand):
            avatar_path = cand
            break
    if avatar_path:
        st.image(avatar_path, caption="Professor McGarry", width=200)

    st.header("Q&A (in-class)")
    st.caption("Ask about today’s TCP/IP lecture (5-layer model). Keep questions on topic.")

    # Show history (user/assistant only)
    for m in st.session_state.messages:
        if m["role"] in ("user", "assistant"):
            with st.chat_message("user" if m["role"] == "user" else "assistant"):
                st.write(m["content"])

    # Chat input
    prompt = st.chat_input("Ask a question about the TCP/IP model…", disabled=(client is None))
    if client is None:
        st.info("Add a valid OPENAI_API_KEY in Settings → Secrets to enable chat.")
    elif prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                temperature=0.3,
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            answer = f"(Error contacting OpenAI: {e})"
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)

