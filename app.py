import os, glob, json
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="INFO 300 — TCP/IP Lecture", layout="wide")

# ---- Load narration ----
with open("narration.json", "r", encoding="utf-8") as f:
    NARR = json.load(f)

# ---- Discover slides and optional intro video ----
slide_imgs = sorted(glob.glob("slides/slide_*.png"))
intro_video_path = "videos/intro.mp4"  # optional short real intro from Prof. McGarry

# ---- State ----
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

# ---- Sidebar: navigation ----
st.sidebar.title("Slides")
for i, path in enumerate(slide_imgs):
    label = os.path.basename(path).replace("slide_", "").replace(".png", "")
    if st.sidebar.button(f"Slide {label}", key=f"nav_{i}"):
        st.session_state.idx = i
        st.rerun()

# ---- Main layout ----
left, right = st.columns([2, 1])

with left:
    st.title("INFO 300 — TCP/IP Model (5-layer)")

    # Optional short intro video (your real face)
    if os.path.exists(intro_video_path):
        with st.expander("Play instructor intro (1–2 min)", expanded=False):
            st.video(intro_video_path)

    # Slide panel
    if slide_imgs:
        cur = slide_imgs[st.session_state.idx]
        slide_num = os.path.basename(cur).replace("slide_", "").replace(".png", "")
        st.markdown(f"### Slide {slide_num}")
        st.image(cur, use_container_width=True)

        st.markdown("#### Narration")
        st.write(NARR.get(slide_num, "No narration found for this slide."))

        # Controls
        cols = st.columns(3)
        if cols[0].button("⏮ Prev", use_container_width=True) and st.session_state.idx > 0:
            st.session_state.idx -= 1
            st.rerun()
        if cols[2].button("Next ⏭", use_container_width=True) and st.session_state.idx < len(slide_imgs)-1:
            st.session_state.idx += 1
            st.rerun()
    else:
        st.warning("No slides found. Please export slides as PNG into the slides/ folder.")

with right:
    st.header("Q&A (in-class)")
    st.caption("Ask about today’s TCP/IP lecture (5-layer model). Keep questions on topic.")

    # Show prior chat
    for m in st.session_state.messages:
        if m["role"] in ("user", "assistant"):
            with st.chat_message("user" if m["role"]=="user" else "assistant"):
                st.write(m["content"])

    prompt = st.chat_input("Ask a question about the TCP/IP model…")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.messages,
            temperature=0.3,
        )
        answer = resp.choices[0].message.content.strip()
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)
