from awg import llm

PROMPT = """You explain a payment guardrail decision to the account owner.
Write 1-2 plain sentences. Do not invent facts.
Action: {action}
Decision: {verdict}
Reason: {reason}
Amount: {amount} USD
Active limits: {limits}."""


async def explain(action: str, verdict: str, reason: str, amount: str, limits: str) -> str:
    prompt = PROMPT.format(
        action=action, verdict=verdict, reason=reason, amount=amount, limits=limits
    )
    try:
        return (await llm.generate(prompt, timeout=15)).strip() or reason
    except llm.LLMUnavailable:
        return reason