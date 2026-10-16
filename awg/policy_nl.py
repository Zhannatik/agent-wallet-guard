import json
from decimal import Decimal, InvalidOperation

from awg import llm
from awg.policy import Policy

PROMPT = """You convert a spending rule written in plain language into JSON.
Return ONLY a JSON object with exactly these keys:
- "max_per_tx": number, maximum amount for a single invoice or payment
- "daily_budget": number, maximum total of invoices or payments per day
- "approval_threshold": number, invoice amounts above this need human approval
- "max_refund": number, maximum amount of a single refund
- "daily_refund_budget": number, maximum total refunds per day
- "refund_approval_threshold": number, refund amounts above this need human approval
- "allowed_recipients": list of email addresses; an empty list means any recipient
Use null for anything the rule does not mention. All amounts are in USD.
Rule: <<<{text}>>>"""

_AMOUNT_KEYS = (
    "max_per_tx", "daily_budget", "approval_threshold",
    "max_refund", "daily_refund_budget", "refund_approval_threshold",
)


def _amount(value, name: str) -> Decimal:
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{name} is not a number: {value!r}")
    if not d.is_finite() or d <= 0:
        raise ValueError(f"{name} must be a positive number")
    return d


def policy_from_data(data: dict, base: Policy) -> Policy:
    """Validate model output in code. The model is never trusted blindly."""
    p = Policy(
        max_per_tx=base.max_per_tx,
        daily_budget=base.daily_budget,
        approval_threshold=base.approval_threshold,
        allowed_recipients=list(base.allowed_recipients),
        max_refund=base.max_refund,
        refund_approval_threshold=base.refund_approval_threshold,
        daily_refund_budget=base.daily_refund_budget,
    )
    for key in _AMOUNT_KEYS:
        if data.get(key) is not None:
            setattr(p, key, _amount(data[key], key))

    recipients = data.get("allowed_recipients")
    if recipients:
        if not all(isinstance(r, str) and "@" in r for r in recipients):
            raise ValueError("allowed_recipients must be email addresses")
        p.allowed_recipients = recipients

    if not (p.approval_threshold <= p.max_per_tx <= p.daily_budget):
        raise ValueError("Inconsistent limits: need approval_threshold <= max_per_tx <= daily_budget")
    if not (p.refund_approval_threshold <= p.max_refund <= p.daily_refund_budget):
        raise ValueError(
            "Inconsistent refund limits: need refund_approval_threshold <= max_refund <= daily_refund_budget"
        )
    return p


async def parse_policy(text: str, base: Policy) -> Policy:
    raw = await llm.generate(PROMPT.format(text=text), json_mode=True)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("The model did not return valid JSON")
    if not isinstance(data, dict):
        raise ValueError("The model returned an unexpected structure")
    return policy_from_data(data, base)