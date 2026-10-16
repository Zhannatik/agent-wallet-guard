from awg import llm
from awg.policy import Policy

PROMPT = """You explain a payment guardrail decision to the account owner.
Write 1-2 plain sentences. Do not invent facts.
Decision: {verdict}
Reason: {reason}
Amount: {amount} USD
Active limits: per transaction {max_per_tx}, per day {daily_budget}, approval above {approval_threshold}."""


async def explain(verdict: str, reason: str, amount: str, policy: Policy) -> str:
    prompt = PROMPT.format(
        verdict=verdict, reason=reason, amount=amount,
        max_per_tx=policy.max_per_tx, daily_budget=policy.daily_budget,
        approval_threshold=policy.approval_threshold,
    )
    try:
        return (await llm.generate(prompt, timeout=15)).strip() or reason
    except llm.LLMUnavailable:
        return reason