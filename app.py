import streamlit as st
import os, glob, itertools
from openai import OpenAI
from streamlit.components.v1 import html

# ===============================
# CONFIG & SETUP
# ===============================
st.set_page_config(layout="wide", page_title="INFO 300 Lecture")

# Load OpenAI client
client = None
if "OPENAI_API_KEY" in st.secrets:
    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except Exception as e:
        st.error(f"Could not initialize OpenAI: {e}")

# Session state init
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tts_cache" not in st.session_state:
    st.session_state.tts_cache = {}
if "intro_shown" not in st.session_state:
    st.session_state.intro_shown = False

# ===============================
# HELPERS
# ===============================
def sorted_slides(folder="slides"):
    """Return sorted list of slide PNGs (natural sort)."""
    patterns = [os.path.join(folder, "*.png"), os.path.join(folder, "*.jpg")]
    all_files = set(itertools.chain.from_iterable(glob.glob(p) for p in patterns))
    return sorted(all_files, key=lambda x: int("".join(filter(str.isdigit, os.path.basename(x))) or 0))

def to_two_digit_slide_num(path, idx):
    fname = os.path.basename(path)
    num = "".join(filter(str.isdigit, fname))
    return num.zfill(2) if num else str(idx + 1).zfill(2)

# Example narration dictionary
NARR = {
    "01": "Welcome to the TCP/IP 5-layer model lecture...",
    "02": "Here’s the application layer overview...",
    # Add more narration here keyed by slide numbers
}

# ===============================
# MAIN LAYOUT
# ===============================
left, right = st.columns([2, 1])

# ----- LEFT: Title, video, slides -----
with left:
    st.title("INFO 300 — TCP/IP Model (5-layer)")

    # --- Intro video ---
from streamlit.components.v1 import html

# ----- Intro video (autoplay once, compact height, JS fallback) -----
intro_video_path = "videos/intro.mp4"
if os.path.exists(intro_video_path):
    if not st.session_state.get("intro_shown", False):
        html(
            """
            <video id="introvid"
                src="videos/intro.mp4"
                autoplay
                muted
                playsinline
                controls
                style="width:100%; height:220px; object-fit:cover; border-radius:12px; outline:none;">
            </video>
            <script>
              const v = document.getElementById('introvid');
              function tryPlay(){
                const p = v.play();
                if (p && p.catch) { p.catch(()=>{}); }
              }
              // Try on load and when enough data is ready
              window.addEventListener('load', tryPlay);
              v.addEventListener('canplay', tryPlay);
            </script>
            """,
            height=240,  # total iframe height; tweak to 200–260 to taste
        )
        st.session_state.intro_shown = True
    else:
        with st.expander("Replay instructor intro", expanded=False):
            st.video(intro_video_path)
else:
    st.info("Intro video not found at videos/intro.mp4")


    # --- Slides ---
    slide_imgs = sorted_slides()
    if not slide_imgs:
        st.warning("No slides found. Please place PNGs in the 'slides/' folder.")
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
                st.warning("OpenAI key missing — cannot synthesize audio.")
            else:
                if slide_num not in st.session_state.tts_cache:
                    try:
                        speech = client.audio.speech.create(
                            model="gpt-4o-mini-tts",
                            voice="alloy",  # change to 'verse' for male-sounding voice
                            input=narration_text,
                        )
                        audio_bytes = speech.content
                        st.session_state.tts_cache[slide_num] = audio_bytes
                    except Exception as e:
                        st.error(f"Audio synthesis failed: {e}")
                if slide_num in st.session_state.tts_cache and st.session_state.tts_cache[slide_num]:
                    st.audio(st.session_state.tts_cache[slide_num], format="audio/mp3")
        if t2.button("⟲ Regenerate audio", key=f"tts_regen_{slide_num}", use_container_width=True) and client:
            st.session_state.tts_cache.pop(slide_num, None)
            st.rerun()

        # Slide navigation
        nav1, nav2, _ = st.columns([1, 1, 4])
        if nav1.button("⬅️ Prev", use_container_width=True):
            st.session_state.idx = max(0, st.session_state.idx - 1)
            st.rerun()
        if nav2.button("Next ➡️", use_container_width=True):
            st.session_state.idx = min(len(slide_imgs) - 1, st.session_state.idx + 1)
            st.rerun()

# ----- RIGHT: Avatar + Q&A -----
with right:
    # Headshot above Q&A
    avatar_path = None
    for cand in ("slides/avatar.jpg", "slides/avatar.png", "avatar.jpg", "avatar.png"):
        if os.path.exists(cand):
            avatar_path = cand
            break
    if avatar_path:
        st.image(avatar_path, caption="Professor McGarry", width=160)

    st.header("Q&A (in-class)")
    st.caption("Ask about today’s TCP/IP lecture (5-layer model). Keep questions on topic.")

    # Display chat history
    for m in st.session_state.messages:
        if m["role"] in ("user", "assistant"):
            with st.chat_message("user" if m["role"] == "user" else "assistant"):
                st.write(m["content"])

    # Input box
    if prompt := st.chat_input("Ask a question about the lecture..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        if client:
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a teaching assistant for an INFO 300 TCP/IP lecture. Keep answers concise and on-topic."},
                        *st.session_state.messages
                    ],
                )
                reply = resp.choices[0].message.content
            except Exception as e:
                reply = f"Error from OpenAI: {e}"
        else:
            reply = "⚠️ OpenAI key missing — cannot answer."

        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.write(reply)
