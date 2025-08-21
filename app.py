import os, glob, itertools, json
import streamlit as st
from openai import OpenAI

# ---------- Page / App Config ----------
st.set_page_config(
    page_title="INFO 300 — TCP/IP Lecture",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- OpenAI client from Secrets ----------
client = None
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")
if OPENAI_KEY:
    try:
        client = OpenAI(api_key=OPENAI_KEY)
    except Exception:
        client = None  # will show friendly messages later

VOICE = st.secrets.get("VOICE", "verse")  # e.g., "verse" (male-ish), "alloy", "aria"

# ---------- Helpers ----------
def numeric_key(path: str) -> int:
    """Extract first number from filename for natural sort; default 0 if none."""
    base = os.path.basename(path)
    digits = "".join(ch for ch in base if ch.isdigit())
    return int(digits) if digits else 0

def two_digit_from_path_or_index(path: str, idx: int) -> str:
    """Return slide number as 2 digits for narration keys."""
    base = os.path.basename(path)
    digits = "".join(ch for ch in base if ch.isdigit())
    if digits:
        return str(int(digits)).zfill(2)
    return str(idx + 2).zfill(2)  # fallback assumes deck starts at slide 2

# ---------- Load narration ----------
NARR = {}
if os.path.exists("narration.json"):
    with open("narration.json", "r", encoding="utf-8") as f:
        NARR = json.load(f)

# ---------- Find slides (flexible + natural numeric sort) ----------
patterns = [
    "slides/slide_*.png", "slides/slide_*.PNG",
    "slides/Slide*.png",  "slides/Slide*.PNG",
    "slides/*.png",       "slides/*.PNG",
]
all_files = set(itertools.chain.from_iterable(glob.glob(p) for p in patterns)))
slide_imgs = sorted(all_files, key=numeric_key)

# ---------- Session State ----------
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tts_cache" not in st.session_state:
    st.session_state.tts_cache = {}   # { "02": b"<mp3 bytes>" }
if "intro_shown" not in st.session_state:
    st.session_state.intro_shown = False

# ---------- Sidebar: slide navigator ----------
st.sidebar.title("Slides")
if slide_imgs:
    for i, path in enumerate(slide_imgs):
        label = two_digit_from_path_or_index(path, i)
        if st.sidebar.button(f"Slide {label}", key=f"nav_{i}"):
            st.session_state.idx = i
            st.rerun()
else:
    st.sidebar.info("No slides detected. Place PNGs in the 'slides/' folder at repo root.")

# ---------- Layout ----------
left, right = st.columns([2, 1])

# ===== LEFT: Title, Intro Video, Slides, Narration, TTS, Nav =====
with left:
    st.title("INFO 300 — TCP/IP Model (5-layer)")

    # ----- Intro video (autoplay once, then replay expander) -----
    intro_video_path = "videos/intro.mp4"
    if os.path.exists(intro_video_path):
        if not st.session_state.intro_shown:
            # Autoplay muted (browser requirement). Use static HTML (no f-string) to avoid paste issues.
            st.markdown(
                """
                <video
                    src="videos/intro.mp4"
                    autoplay
                    muted
                    playsinline
                    controls
                    style="width:100%; border-radius:12px; outline:none;"
                ></video>
                """,
                unsafe_allow_html=True
            )
            st.session_state.intro_shown = True
        else:
            with st.expander("Replay instructor intro", expanded=False):
                st.video(intro_video_path)

    # ----- Slide viewer -----
    if not slide_imgs:
        st.warning("No slides found. Please place PNGs in the 'slides/' folder.")
    else:
        cur = slide_imgs[st.session_state.idx]
        slide_num = two_digit_from_path_or_index(cur, st.session_state.idx)

        st.markdown(f"### Slide {slide_num}")
        st.image(cur, use_container_width=True)

        st.markdown("#### Narration")
        narration_text = NARR.get(slide_num, "No narration found for this slide.")
        st.write(narration_text)

        # ---- Audio narration (TTS) ----
        t1, t2, _ = st.columns([1, 1, 3])
        if t1.button("▶️ Play audio narration", key=f"tts_{slide_num}", use_container_width=True):
            if not client:
                st.warning("OpenAI key missing or invalid — cannot synthesize audio.")
            else:
                if slide_num not in st.session_state.tts_cache:
                    try:
                        speech = client.audio.speech.create(
                            model="gpt-4o-mini-tts",
                            voice=VOICE,
                            input=narration_text,
                        )
                        audio_bytes = speech.content  # recent SDKs return bytes here
                        st.session_state.tts_cache[slide_num] = audio_bytes
                    except Exception as e:
                        st.error(f"Audio synthesis failed: {e}")
                if st.session_state.tts_cache.get(slide_num):
                    st.audio(st.session_state.tts_cache[slide_num], format="audio/mp3")

        if t2.button("⟲ Regenerate audio", key=f"tts_regen_{slide_num}", use_container_width=True) and client:
            st.session_state.tts_cache.pop(slide_num, None)
            st.rerun()

        # ---- Prev / Next buttons ----
        n1, n2, n3 = st.columns([1, 4, 1])
        if n1.button("⬅️ Prev", use_container_width=True):
            st.session_state.idx = max(0, st.session_state.idx - 1)
            st.rerun()
        n2.write(f"Slide {st.session_state.idx + 1} of {len(slide_imgs)}")
        if n3.button("Next ➡️", use_container_width=True):
            st.session_state.idx = min(len(slide_imgs) - 1, st.session_state.idx + 1)
            st.rerun()

# ===== RIGHT: Avatar (above Q&A) + Q&A =====
with right:
    # Headshot ABOVE Q&A — check slides/ first, then repo root
    avatar_path = None
    for cand in ("slides/avatar.jpg", "slides/avatar.png", "avatar.jpg", "avatar.png"):
        if os.path.exists(cand):
            avatar_path = cand
            break
    if avatar_path:
        st.image(avatar_path, caption="Professor McGarry", use_container_width=True)

    st.header("Q&A (in-class)")
    st.caption("Ask about today’s TCP/IP lecture (5-layer model). Keep questions on topic.")

    # Chat history
    for m in st.session_state.messages:
        if m["role"] in ("user", "assistant"):
            with st.chat_message("user" if m["role"] == "user" else "assistant"):
                st.write(m["content"])

    # Chat input
    prompt = st.chat_input("Ask a question about TCP/IP…", disabled=(client is None))
    if not client and prompt:
        st.info("OpenAI key missing — add it in Settings → Secrets to enable chat.")
    elif client and prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful TA for INFO 300. Keep answers concise and on-topic about the TCP/IP model (5-layer)."},
                    *st.session_state.messages,
                ],
                temperature=0.3,
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"(Error contacting OpenAI: {e})"
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)
