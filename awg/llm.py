import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMUnavailable(RuntimeError):
    pass


async def _generate(prompt: str, json_mode: bool = False, timeout: float = 60) -> str:
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

_checked = False
_client = None


def _langfuse():
    """Клиент Langfuse или None, если ключей нет или SDK недоступен."""
    global _checked, _client
    if _checked:
        return _client
    _checked = True
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return None
    try:
        from langfuse import get_client
        _client = get_client()
    except Exception:
        _client = None
    return _client


def _safe(fn) -> None:
    try:
        fn()
    except Exception:
        pass  # трассировка никогда не должна ломать решения


async def generate(prompt: str, json_mode: bool = False, timeout: float = 60, name: str = "gemini") -> str:
    lf = _langfuse()
    if lf is None:
        return await _generate(prompt, json_mode, timeout)
    model = os.getenv("GEMINI_MODEL") or "gemini-flash-lite-latest"
    try:
        cm = lf.start_as_current_observation(as_type="generation", name=name, model=model, input=prompt)
        gen = cm.__enter__()
    except Exception:
        return await _generate(prompt, json_mode, timeout)
    try:
        out = await _generate(prompt, json_mode, timeout)
    except Exception as e:
        _safe(lambda: gen.update(level="ERROR", status_message=str(e)[:300]))
        _safe(lambda: cm.__exit__(type(e), e, e.__traceback__))
        raise
    _safe(lambda: gen.update(output=out))
    _safe(lambda: cm.__exit__(None, None, None))
    return out


def flush() -> None:
    lf = _langfuse()
    if lf is not None:
        _safe(lf.flush)