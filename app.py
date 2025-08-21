import os
import re
import glob
import itertools
import json
import streamlit as st
from openai import OpenAI

# ===============================
# Page setup
# ===============================
st.set_page_config(
    page_title="INFO 300 — TCP/IP Lecture",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===============================
# OpenAI client (from Secrets)
# ===============================
client = None
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")
if OPENAI_KEY:
    try:
        client = OpenAI(api_key=OPENAI_KEY)
    except Exception:
        client = None  # We'll show a friendly message in the UI

VOICE = st.secrets.get("VOICE", "verse")  # try "verse", "alloy", or "aria"

# ===============================
# Helpers
# ===============================
def load_narration() -> dict:
    """
    Load narration from narration.json at repo root.
    Normalize keys to 2 digits: "2" -> "02".
    """
    try:
        with open("narration.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return {str(k).zfill(2): v for k, v in data.items()}
    except Exception as e:
        st.warning(f"Failed to load narration.json: {e}")
        return {}

def discover_slides(folder: str = "slides") -> list:
    """
    Find slide images and return a naturally sorted list by first number in filename.
    Supports .png/.jpg (any case).
    """
    patterns = [
        os.path.join(folder, "*.png"),
        os.path.join(folder, "*.PNG"),
        os.path.join(folder, "*.jpg"),
        os.path.join(folder, "*.JPG"),
        os.path.join(folder, "Slide*.png"),
        os.path.join(folder, "Slide*.PNG"),
    ]
    all_files = set(itertools.chain.from_iterable(glob.glob(p) for p in patterns))
    def numeric_key(path: str) -> int:
        m = re.search(r"(\d+)", os.path.basename(path))
        return int(m.group(1)) if m else 0
    return sorted(all_files, key=numeric_key)

def slide_key_for(path: str, idx: int) -> str:
    """
    Derive a 2-digit narration key from a slide filename.
    If no digits are present, fall back to 1-based index.
    """
    m = re.search(r"(\d+)", os.path.basename(path))
    n = int(m.group(1)) if m else (idx + 1)
    return f"{n:02d}"

def find_avatar() -> str | None:
    for cand in ("slides/avatar.jpg", "slides/avatar.png", "avatar.jpg", "avatar.png"):
        if os.path.exists(cand):
            return cand
    return None

# ===============================
# Data
# ===============================
NARR = load_narration()
slide_imgs = discover_slides()

# ===============================
# Session state
# ===============================
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tts_cache" not in st.session_state:
    st.session_state.tts_cache = {}  # { "02": b"<mp3 bytes>" }

# ===============================
# Sidebar: slide navigator
# ===============================
st.sidebar.title("Slides")
if slide_imgs:
    for i, path in enumerate(slide_imgs):
        label = slide_key_for(path, i)
        if st.sidebar.button(f"Slide {label}", key=f"nav_{i}"):
            st.session_state.idx = i
            st.rerun()
else:
    st.sidebar.info("No slides detected. Put PNG/JPG files in the `slides/` folder.")

# ===============================
# Layout
# ===============================
left, right = st.columns([2, 1])

# ----- LEFT column: slides, narration, audio, nav -----
with left:
    st.title("INFO 300 — TCP/IP Model (5-layer)")

    if not slide_imgs:
        st.warning("No slides found. Please place PNG/JPGs in the 'slides/' folder.")
    else:
        cur = slide_imgs[st.session_state.idx]
        key = slide_key_for(cur, st.session_state.idx)

        st.markdown(f"### Slide {key}")
        st.image(cur, use_container_width=True)

        st.markdown("#### Narration")
        narration_text = NARR.get(key, "No narration found for this slide.")
        st.write(narration_text)

        # Audio narration (text-to-speech)
        c1, c2, _ = st.columns([1, 1, 3])
        if c1.button("▶️ Play audio narration", key=f"tts_{key}", use_container_width=True):
            if not client:
                st.warning("OpenAI key missing or invalid — cannot synthesize audio.")
            else:
                if key not in st.session_state.tts_cache:
                    try:
                        speech = client.audio.speech.create(
                            model="gpt-4o-mini-tts",
                            voice=VOICE,
                            input=narration_text,
                        )
                        audio_bytes = speech.content  # recent SDKs return bytes here
                        st.session_state.tts_cache[key] = audio_bytes
                    except Exception as e:
                        st.error(f"Audio synthesis failed: {e}")
                if st.session_state.tts_cache.get(key):
                    st.audio(st.session_state.tts_cache[key], format="audio/mp3")

        if c2.button("⟲ Regenerate audio", key=f"tts_regen_{key}", use_container_width=True) and client:
            st.session_state.tts_cache.pop(key, None)
            st.rerun()

        # Prev / Next
        n1, n2, n3 = st.columns([1, 4, 1])
        if n1.button("⬅️ Prev", use_container_width=True):
            st.session_state.idx = max(0, st.session_state.idx - 1)
            st.rerun()
        n2.caption(f"Slide {st.session_state.idx + 1} of {len(slide_imgs)}")
        if n3.button("Next ➡️", use_container_width=True):
            st.session_state.idx = min(len(slide_imgs) - 1, st.session_state.idx + 1)
            st.rerun()

# ----- RIGHT column: avatar + Q&A -----
with right:
    avatar = find_avatar()
    if avatar:
        st.image(avatar, caption="Professor McGarry", width=160)

    st.header("Q&A (in-class)")
    st.caption("Ask about today’s TCP/IP lecture (5-layer model). Keep questions on topic.")

    for m in st.session_state.messages:
        if m["role"] in ("user", "assistant"):
            with st.chat_message("user" if m["role"] == "user" else "assistant"):
                st.write(m["content"])

    prompt = st.chat_input("Ask a question about the TCP/IP model…", disabled=(client is None))
    if prompt and not client:
        st.info("OpenAI key missing — add it under Settings → Secrets to enable chat.")
    elif prompt and client:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "You are a helpful TA for INFO 300. "
                        "Answer concisely and stay on-topic about the TCP/IP model (5-layer)."
                    )},
                    *st.session_state.messages,
                ],
                temperature=0.3,
            )
            answer = resp.choices[0].message.content
        except Exception as e:
            answer = f"(Error contacting OpenAI: {e})"
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)

