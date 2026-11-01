import chainlit as cl
from agents import Runner
from agents_config import travel_router

MOODS = {
    "Education": "🎓 Education",
    "Business": "💼 Business",
    "Travelling": "🧳 Travelling",
    "Explore": "🧭 Explore",
}
MOOD_EMOJI = {k: v.split()[0] for k, v in MOODS.items()}


async def ask_text(prompt: str) -> str:
    res = await cl.AskUserMessage(content=prompt, timeout=600).send()
    return (res or {}).get("output", "").strip()


async def run_agent(text: str):
    """Router ko chalata hai aur jawab UI mein dikhata hai."""
    history = cl.user_session.get("chat_history", [])
    next_input = [*history, {"role": "user", "content": text}]

    async with cl.Step(name="Multi-agent workflow", show_input=True) as step:
        step.input = text
        try:
            result = await Runner.run(travel_router, next_input, max_turns=8)
            cl.user_session.set("chat_history", result.to_input_list())

            guide_name = result.last_agent.name
            answer = str(result.final_output)
            step.output = f"Completed. Final responding agent: {guide_name}"

            await cl.Message(
                content=f"**Responding agent:** {guide_name}\n\n{answer}"
            ).send()
        except Exception as exc:
            print("Agent run failed:", repr(exc))
            step.output = f"Failed: {type(exc).__name__}"
            await cl.Message(
                content=(
                    "Sorry, the agent run failed. Check the VS Code terminal "
                    "for the error, then verify your API key, model, and internet."
                )
            ).send()


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("chat_history", [])
    cl.user_session.set("ready", False)

    await cl.Message(
        content="## ✈️ Travel Suggestion Agent\nMain aapka 10 din ka travel plan banaunga."
    ).send()

    # 1) Name
    name = await ask_text("What is your name?")

    # 2) Country
    country = await ask_text(
        f"Nice to meet you, {name}! Which country do you want to visit?"
    )

    # 3) Mood
    res = await cl.AskActionMessage(
        content=f"What is your mood for {country}?",
        actions=[
            cl.Action(name="mood", payload={"value": k}, label=v) for k, v in MOODS.items()
        ],
        timeout=600,
    ).send()
    mood = (res or {}).get("payload", {}).get("value") or "Travelling"

    # 4) Budget
    budget = await ask_text(
        "What is your total budget for this trip? (e.g. PKR 300,000 or $1500)"
    )

    # Trip summary card (markdown table, CSS se styled)
    await cl.Message(
        content=(
            f"### 🌍 Trip Summary\n\n"
            f"| | |\n|---|---|\n"
            f"| 👤 **Traveller** | {name} |\n"
            f"| 📍 **Destination** | {country} |\n"
            f"| {MOOD_EMOJI.get(mood, '🧳')} **Mood** | {mood} |\n"
            f"| 💰 **Budget** | {budget} |\n"
            f"| 📅 **Duration** | 10 days |\n\n"
            f"> ⏳ {name}, aapka plan ban raha hai..."
        )
    ).send()

    # 5) Plan
    await run_agent(
        f"Traveller name: {name}\n"
        f"Country: {country}\n"
        f"Mood: {mood}\n"
        f"Budget: {budget}\n\n"
        "Please make my complete 10-day travel plan."
    )
    cl.user_session.set("ready", True)


@cl.on_message
async def on_message(message: cl.Message):
    if not cl.user_session.get("ready"):
        await cl.Message(content="Pehle upar ke sawalon ke jawab dein 🙂").send()
        return
    await run_agent(message.content)
