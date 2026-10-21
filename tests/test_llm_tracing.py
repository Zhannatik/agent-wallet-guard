import asyncio

from awg import llm


def _reset(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setattr(llm, "_checked", False)
    monkeypatch.setattr(llm, "_client", None)

    async def fake(prompt, json_mode=False, timeout=60):
        return "ok"

    monkeypatch.setattr(llm, "_generate", fake)


def test_works_without_langfuse_keys(monkeypatch):
    _reset(monkeypatch)
    assert asyncio.run(llm.generate("x")) == "ok"


def test_broken_tracing_does_not_break_generate(monkeypatch):
    _reset(monkeypatch)

    class Broken:
        def start_as_current_observation(self, **kw):
            raise RuntimeError("langfuse down")

        def flush(self):
            raise RuntimeError("langfuse down")

    monkeypatch.setattr(llm, "_checked", True)
    monkeypatch.setattr(llm, "_client", Broken())
    assert asyncio.run(llm.generate("x")) == "ok"
    llm.flush()