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
    max_refund: Decimal = Decimal("50")
    refund_approval_threshold: Decimal = Decimal("20")
    daily_refund_budget: Decimal = Decimal("100")


@dataclass
class Decision:
    verdict: Verdict
    reason: str


def _parse(amount: str) -> Decimal | None:
    try:
        value = Decimal(amount)
    except InvalidOperation:
        return None
    if not value.is_finite() or value <= 0:
        return None
    return value


def describe_limits(p: Policy, kind: str = "invoice") -> str:
    if kind == "refund":
        return (f"per refund {p.max_refund}, per day {p.daily_refund_budget}, "
                f"approval above {p.refund_approval_threshold}")
    return (f"per transaction {p.max_per_tx}, per day {p.daily_budget}, "
            f"approval above {p.approval_threshold}")


def evaluate(amount: str, recipient: str, spent_today: Decimal, policy: Policy) -> Decision:
    value = _parse(amount)
    if value is None:
        return Decision(Verdict.DENY, "Invalid or non-positive amount")

    if policy.allowed_recipients and recipient.lower() not in (
        r.lower() for r in policy.allowed_recipients
    ):
        return Decision(Verdict.DENY, "Recipient is not on the allowed list")

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


def evaluate_refund(amount: str, refunded_today: Decimal, policy: Policy) -> Decision:
    value = _parse(amount)
    if value is None:
        return Decision(Verdict.DENY, "Invalid or non-positive amount")

    if value > policy.max_refund:
        return Decision(Verdict.DENY, f"{value} exceeds the per-refund limit of {policy.max_refund}")

    if refunded_today + value > policy.daily_refund_budget:
        return Decision(
            Verdict.DENY,
            f"Daily refund budget of {policy.daily_refund_budget} would be exceeded (refunded {refunded_today})",
        )

    if value > policy.refund_approval_threshold:
        return Decision(
            Verdict.NEEDS_APPROVAL,
            f"{value} is above the refund approval threshold of {policy.refund_approval_threshold}",
        )

    return Decision(Verdict.ALLOW, "Within policy")