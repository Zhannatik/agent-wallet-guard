import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMUnavailable(RuntimeError):
    pass


async def generate(prompt: str, json_mode: bool = False, timeout: float = 60) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise LLMUnavailable("GEMINI_API_KEY is not set")
    model = os.getenv("GEMINI_MODEL") or "gemini-flash-lite-latest"

    config = {"temperature": 0}
    if json_mode:
        config["responseMimeType"] = "application/json"
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                API.format(model=model), headers={"x-goog-api-key": key}, json=body
            )
    except httpx.TimeoutException:
        raise LLMUnavailable(f"Gemini did not answer within {timeout:.0f}s")
    except httpx.HTTPError as e:
        raise LLMUnavailable(f"Network error talking to Gemini: {e}")

    if r.is_error:
        raise LLMUnavailable(f"Gemini error {r.status_code}: {r.text[:300]}")
    try:
        parts = r.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError):
        raise LLMUnavailable("Unexpected Gemini response format")