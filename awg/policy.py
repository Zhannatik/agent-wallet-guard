from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum


class Verdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    NEEDS_APPROVAL = "needs_approval"


@dataclass
class Policy:
    max_per_tx: Decimal = Decimal("100")
    daily_budget: Decimal = Decimal("500")
    approval_threshold: Decimal = Decimal("50")
    allowed_recipients: list[str] = field(default_factory=list)  # пусто = любые


@dataclass
class Decision:
    verdict: Verdict
    reason: str


def evaluate(amount: str, recipient: str, spent_today: Decimal, policy: Policy) -> Decision:
    try:
        value = Decimal(amount)
    except InvalidOperation:
        return Decision(Verdict.DENY, f"Invalid amount: {amount!r}")
    if value <= 0:
        return Decision(Verdict.DENY, "Amount must be positive")

    if policy.allowed_recipients and recipient.lower() not in (
        r.lower() for r in policy.allowed_recipients
    ):
        return Decision(Verdict.DENY, f"Recipient {recipient} is not on the allowed list")

    if value > policy.max_per_tx:
        return Decision(Verdict.DENY, f"{value} exceeds the per-transaction limit of {policy.max_per_tx}")

    if spent_today + value > policy.daily_budget:
        return Decision(
            Verdict.DENY,
            f"Daily budget of {policy.daily_budget} would be exceeded (spent {spent_today})",
        )

    if value > policy.approval_threshold:
        return Decision(Verdict.NEEDS_APPROVAL, f"{value} is above the approval threshold of {policy.approval_threshold}")

    return Decision(Verdict.ALLOW, "Within policy")

DEFAULT_POLICY = Policy()