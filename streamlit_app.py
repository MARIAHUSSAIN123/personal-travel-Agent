import asyncio
import os

import streamlit as st
from agents import Runner
from openai import RateLimitError

st.set_page_config(page_title="Safar - Travel Agent", page_icon="✈️", layout="centered")

# Streamlit Secrets ko environment variables bana do (local run par .env use hoti hai)
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, (str, int, float, bool)):
            os.environ.setdefault(_k, str(_v))
except Exception:
    pass

from agents_config import travel_router  # noqa: E402

MOODS = {
    "🎓 Education": "Education",
    "💼 Business": "Business",
    "🧳 Travelling": "Travelling",
    "🧭 Explore": "Explore",
}
RETRY_WAIT = 30
MAX_RETRIES = 5


async def run_agent(history: list, text: str):
    """Router chalata hai; 429 (free quota) par intezar karke dobara try karta hai."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await Runner.run(
                travel_router, [*history, {"role": "user", "content": text}], max_turns=8
            )
        except RateLimitError:
            if attempt == MAX_RETRIES:
                raise
            st.toast(f"⏳ Free quota limit. {RETRY_WAIT}s ruk kar dobara try ({attempt}/{MAX_RETRIES})")
            await asyncio.sleep(RETRY_WAIT)


def ask(text: str):
    """Agent ko chalata hai aur history + jawab session_state mein save karta hai."""
    result = asyncio.run(run_agent(st.session_state.history, text))
    st.session_state.history = result.to_input_list()
    return result.last_agent.name, str(result.final_output)


# ------------------------------- State -------------------------------
st.session_state.setdefault("history", [])
st.session_state.setdefault("messages", [])  # [(role, text)]
st.session_state.setdefault("profile", None)

# ------------------------------- UI -------------------------------
st.title("✈️ Safar - Travel Suggestion Agent")
st.caption("Country, mood aur budget batayein, aapka 10 din ka plan tayyar.")

if st.session_state.profile is None:
    with st.form("trip_form"):
        name = st.text_input("👤 What is your name?")
        country = st.text_input("📍 Which country do you want to visit?")
        mood_label = st.radio("🎯 What is your mood?", list(MOODS), horizontal=True)
        budget = st.text_input("💰 What is your total budget?", placeholder="PKR 300,000 ya $1500")
        submitted = st.form_submit_button("🚀 Make my 10-day plan", type="primary")

    if submitted:
        if not (name.strip() and country.strip() and budget.strip()):
            st.error("Naam, country aur budget teeno likhein.")
        else:
            mood = MOODS[mood_label]
            st.session_state.profile = {
                "name": name.strip(), "country": country.strip(),
                "mood": mood, "mood_label": mood_label, "budget": budget.strip(),
            }
            request = (
                f"Traveller name: {name.strip()}\n"
                f"Country: {country.strip()}\n"
                f"Mood: {mood}\n"
                f"Budget: {budget.strip()}\n\n"
                "Please make my complete 10-day travel plan."
            )
            try:
                with st.spinner(f"⏳ {name.strip()}, aapka plan ban raha hai..."):
                    agent_name, answer = ask(request)
                st.session_state.messages.append(
                    ("assistant", f"**Responding agent:** {agent_name}\n\n{answer}")
                )
            except Exception as exc:
                st.session_state.profile = None
                st.session_state.history = []
                st.error(f"Run fail ho gaya: {type(exc).__name__}: {str(exc)[:400]}")
            st.rerun() if st.session_state.profile else None
else:
    p = st.session_state.profile
    st.subheader("🌍 Trip Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👤 Traveller", p["name"])
    c2.metric("📍 Destination", p["country"])
    c3.metric("🎯 Mood", p["mood_label"])
    c4.metric("💰 Budget", p["budget"])
    st.divider()

    # Follow-up sawal
    if prompt := st.chat_input("Plan ke baare mein kuch bhi puchein..."):
        st.session_state.messages.append(("user", prompt))
        try:
            with st.spinner("Soch raha hoon..."):
                agent_name, answer = ask(prompt)
            st.session_state.messages.append(
                ("assistant", f"**Responding agent:** {agent_name}\n\n{answer}")
            )
        except Exception as exc:
            st.error(f"Run fail ho gaya: {type(exc).__name__}: {str(exc)[:400]}")

    for role, text in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(text)

    if st.sidebar.button("🔄 New trip"):
        for k in ("history", "messages", "profile"):
            st.session_state.pop(k, None)
        st.rerun()
