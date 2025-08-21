import os
import glob
import itertools
import streamlit as st
from openai import OpenAI

# ---------------------------
# App setup
# ---------------------------
st.set_page_config(
    page_title="INFO 300 — TCP/IP Lecture",
    layout="wide",
)

# OpenAI client
client = None
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ---------------------------
# Helpers
# ---------------------------
def sorted_slides(folder="slides"):
    patterns = [os.path.join(folder, "*.png"), os.path.join(folder, "*.jpg")]
    all_files = set(itertools.chain.from_iterable(glob.glob(p) for p in patterns))
    # Sort by number if digits exist, else alphabetically
    return sorted(all_files, key=lambda f: int(''.join(filter(str.isdigit, os.path.basename(f))) or 0))

def to_two_digit_slide_num(fname, idx):
    # Extract digits from filename or fallback to index
    digits = ''.join(filter(str.isdigit, os.path.basename(fname)))
    num = int(digits) if digits else idx + 1
    return f"{num:02d}"

def find_avatar():
    for cand in ("slides/avatar.jpg", "slides/avatar.png", "avatar.jpg", "avatar.png"):
        if os.path.exists(cand):
            return cand
    return None

# Example narration (replace with your lecture notes)
NARR = {
    "01": "Welcome to the TCP/IP 5-layer model lecture.",
    "02": "The application layer provides network services to applications.",
    "03": "The transport layer ensures reliable data transfer.",
    "04": "The internet layer handles logical addressing and routing.",
    "05": "The link layer deals with physical addressing and media access.",
}

# ---------------------------
# Session state
# ---------------------------
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tts_cache" not in st.session_state:
    st.session_state.tts_cache = {}

# ---------------------------
# Layout
# ---------------------------
left, right = st.columns([2, 1])

with left:
    st.title("INFO 300 — TCP/IP Model (5-layer)")

    # Slides
    slide_imgs = sorted_slides()
    if not slide_imgs:
        st.warning("No slides found. Please place PNG/JPGs in the 'slides/' folder.")
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
                            voice="alloy",  # change to "verse" or "sage" for different style
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

        # Navigation
        n1, n2, n3 = st.columns([1, 1, 5])
        if n1.button("⬅️ Prev", use_container_width=True):
            st.session_state.idx = max(0, st.session_state.idx - 1)
            st.rerun()
        if n2.button("Next ➡️", use_container_width=True):
            st.session_state.idx = min(len(slide_imgs) - 1, st.session_state.idx + 1)
            st.rerun()
        n3.caption(f"Slide {st.session_state.idx+1} of {len(slide_imgs)}")

with right:
    # Headshot above Q&A
    avatar_path = find_avatar()
    if avatar_path:
        st.image(avatar_path, caption="Professor McGarry", width=160)

    st.header("Q&A (in-class)")
    st.caption("Ask about today’s TCP/IP lecture (5-layer model). Keep questions on topic.")

    # Show chat history
    for m in st.session_state.messages:
        if m["role"] in ("user", "assistant"):
            with st.chat_message("user" if m["role"] == "user" else "assistant"):
                st.write(m["content"])

    # New input
    if q := st.chat_input("Enter your question:"):
        st.session_state.messages.append({"role": "user", "content": q})
        if client:
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful teaching assistant for TCP/IP 5-layer model."},
                        {"role": "user", "content": q},
                    ],
                )
                answer = resp.choices[0].message.content
            except Exception as e:
                answer = f"(Error: {e})"
        else:
            answer = "OpenAI key missing — cannot answer."
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
