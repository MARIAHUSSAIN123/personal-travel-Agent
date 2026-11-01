import os

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel, set_tracing_disabled

load_dotenv()  # local .env; Streamlit Cloud par Secrets environment variables ban jate hain

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

if not api_key or api_key == "replace_me":
    raise RuntimeError("GEMINI_API_KEY missing hai (.env ya Streamlit Secrets mein daalein).")

set_tracing_disabled(True)

# Streamlit har click par naya event loop banata hai, isliye purane connections reuse nahi karte.
client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    max_retries=5,
    http_client=httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=0),
        timeout=120,
    ),
)

gemini_model = OpenAIChatCompletionsModel(
    model=model_name,
    openai_client=client,
)