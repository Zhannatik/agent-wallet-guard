from decimal import Decimal

from awg.policy import Policy, Verdict, evaluate

P = Policy(max_per_tx=Decimal("100"), daily_budget=Decimal("150"),
           approval_threshold=Decimal("50"))


def test_small_amount_allowed():
    assert evaluate("10", "a@b.com", Decimal("0"), P).verdict == Verdict.ALLOW


def test_above_threshold_needs_approval():
    assert evaluate("75", "a@b.com", Decimal("0"), P).verdict == Verdict.NEEDS_APPROVAL


def test_above_per_tx_limit_denied():
    assert evaluate("101", "a@b.com", Decimal("0"), P).verdict == Verdict.DENY


def test_daily_budget_denied():
    assert evaluate("40", "a@b.com", Decimal("120"), P).verdict == Verdict.DENY


def test_invalid_amount_denied():
    assert evaluate("abc", "a@b.com", Decimal("0"), P).verdict == Verdict.DENY


def test_recipient_not_allowed():
    pol = Policy(allowed_recipients=["ok@b.com"])
    assert evaluate("10", "bad@b.com", Decimal("0"), pol).verdict == Verdict.DENY