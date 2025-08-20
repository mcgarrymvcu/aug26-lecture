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
all_files = set(itertools.chain.from_iterable(glob.glob(p) for p in patterns)))

def extract_slide_number(path: str) -> int:
    """Pull first number from filename. If none, put it at the end (9999)."""
    m = re.search(r"(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else 9999

# natural numeric sort: Slide1, Slide2, ... Slide10
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

# ---------- OpenAI client from Secrets ----------
def get_openai_client():
    key = st.secrets.get("OPENAI_API_KEY", "")
    if not key:
        st.sidebar.error("OPENAI_API_KEY is missing in Settings → Secrets. Chat is disabled.")
        return None
    try:
        return OpenAI(api_key=key)
    except Exception as e:
        st.sidebar.error(f"OpenAI init failed: {e}")
        return None

client = get_openai_client()

# ---------- Sidebar: slide navigator ----------
st.sidebar.title("Slides")
if slide_imgs:
    for i, path in enumerate(slide_imgs):
        label = to_two_digit_slide_num(path, i)
        if st.sidebar.button(f"Slide {label}", key=f"nav_{i}"):
            st.session_state.idx = i
            st.rerun()
else:
    st.sidebar.info("No slides detected yet. Ensure PNGs are in the 'slides/' folder at repo root.")

# ---------- Main layout ----------
left, right = st.columns([2, 1])

with left:
    st.title("INFO 300 — TCP/IP Model (5-layer)")

    # Optional short real intro
    intro_video_path = "videos/intro.mp4"
    if os.path.exists(intro_video_path):
        with st.expander("Play instructor intro (1–2 min)", expanded=False):
            st.video(intro_video_path)

    if not slide_imgs:
        st.warning("No slides found. Please place PNGs in the 'slides/' folder.")
    else:
        cur = slide_imgs[st.session_state.idx]
        slide_num = to_two_digit_slide_num(cur, st.session_state.idx)

        st.markdown(f"### Slide {slide_num}")
        st.image(cur, use_container_width=True)

        st.markdown("#### Narration")
        st.write(NARR.get(slide_num, "No narration found for this slide."))

        c1, _, c3 = st.columns([1, 1, 1])
        if c1.button("⏮ Prev", use_container_width=True) and st.session_state.idx > 0:
            st.session_state.idx -= 1
            st.rerun()
        if c3.button("Next ⏭", use_container_width=True) and st.session_state.idx < len(slide_imgs) - 1:
            st.session_state.idx += 1
            st.rerun()

with right:
    st.header("Q&A (in-class)")
    st.caption("Ask about today’s TCP/IP lecture (5-layer model). Keep questions on topic.")

    # Show history (user/assistant only)
    for m in st.session_state.messages:
        if m["role"] in ("user", "assistant"):
            with st.chat_message("user" if m["role"] == "user" else "assistant"):
                st.write(m["content"])

    # Chat input (disabled if no key)
    prompt = st.chat_input("Ask a question about the TCP/IP model…", disabled=(client is None))
    if client is None:
        st.info("Add your OpenAI key in Settings → Secrets to enable chat.")
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

