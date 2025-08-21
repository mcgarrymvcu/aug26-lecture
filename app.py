import streamlit as st
import os, glob, itertools
from openai import OpenAI

# ---------------------------
# Setup
# ---------------------------
st.set_page_config(layout="wide")

client = None
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Cache for TTS
if "tts_cache" not in st.session_state:
    st.session_state.tts_cache = {}

# Cache for chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Slide index
if "idx" not in st.session_state:
    st.session_state.idx = 0

# ---------------------------
# Load slides
# ---------------------------
patterns = ["slides/*.png", "slides/*.jpg"]
all_files = set(itertools.chain.from_iterable(glob.glob(p) for p in patterns))
slide_imgs = sorted(all_files)

def to_two_digit_slide_num(path, idx):
    base = os.path.basename(path)
    num = os.path.splitext(base)[0]
    if num.isdigit():
        return num.zfill(2)
    return str(idx+1).zfill(2)

# Example narration dictionary
NARR = {
    "01": "Welcome to the TCP/IP model lecture. We’ll cover the 5-layer stack.",
    "02": "Physical layer: where signals are transmitted over media.",
    "03": "Data Link layer: frames, MAC addresses, error detection.",
    # Add more narrations as needed
}

# ---------------------------
# Layout
# ---------------------------
left, right = st.columns([2,1])

with left:
    st.title("INFO 300 — TCP/IP Model (5-layer)")

    # ----- Slides -----
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

        # ---- Audio narration ----
        t1, t2, _ = st.columns([1, 1, 3])
        if t1.button("▶️ Play audio narration", key=f"tts_{slide_num}", use_container_width=True):
            if client is None:
                st.warning("OpenAI key missing — cannot synthesize audio.")
            else:
                if slide_num not in st.session_state.tts_cache:
                    try:
                        speech = client.audio.speech.create(
                            model="gpt-4o-mini-tts",
                            voice="alloy",   # voices: alloy, verse, aria
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

        # ---- Navigation ----
        nav1, nav2, nav3 = st.columns([1,1,4])
        if nav1.button("⬅️ Prev", use_container_width=True):
            if st.session_state.idx > 0:
                st.session_state.idx -= 1
                st.rerun()
        if nav2.button("Next ➡️", use_container_width=True):
            if st.session_state.idx < len(slide_imgs)-1:
                st.session_state.idx += 1
                st.rerun()

with right:
    st.header("Q&A (in-class)")
    st.caption("Ask about today’s TCP/IP lecture (5-layer model). Keep questions on topic.")

    # Headshot avatar
    if os.path.exists("avatar.jpg"):
        st.markdown(
            """
            <style>
              .avatar-img {
                max-height: 120px;
                width: auto;
                border-radius: 12px;
                display: block;
                margin: 6px auto 10px auto;
              }
              .avatar-caption {
                text-align: center;
                font-size: 0.85rem;
                color: rgba(0,0,0,0.6);
                margin-top: -6px;
              }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.markdown('<img src="avatar.jpg" class="avatar-img">', unsafe_allow_html=True)
        st.markdown('<div class="avatar-caption">Professor McGarry</div>', unsafe_allow_html=True)

    # Show chat history
    for m in st.session_state.messages:
        if m["role"] in ("user", "assistant"):
            with st.chat_message("user" if m["role"]=="user" else "assistant"):
                st.write(m["content"])

    # Input
    if prompt := st.chat_input("Type your question here..."):
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.chat_message("user"):
            st.write(prompt)

        if client:
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role":"system","content":"You are a helpful teaching assistant answering questions about the TCP/IP 5-layer model lecture."},
                        *st.session_state.messages
                    ]
                )
                answer = resp.choices[0].message.content
            except Exception as e:
                answer = f"(Error: {e})"
        else:
            answer = "(No API key configured — cannot respond.)"

        st.session_state.messages.append({"role":"assistant","content":answer})
        with st.chat_message("assistant"):
            st.write(answer)

