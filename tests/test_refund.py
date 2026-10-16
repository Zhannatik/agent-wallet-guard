from decimal import Decimal

from awg.policy import Policy, Verdict, evaluate_refund

P = Policy(max_refund=Decimal("50"), refund_approval_threshold=Decimal("20"),
           daily_refund_budget=Decimal("60"))


def test_small_refund_allowed():
    assert evaluate_refund("10", Decimal("0"), P).verdict == Verdict.ALLOW


def test_above_threshold_needs_approval():
    assert evaluate_refund("25", Decimal("0"), P).verdict == Verdict.NEEDS_APPROVAL


def test_above_max_denied():
    assert evaluate_refund("51", Decimal("0"), P).verdict == Verdict.DENY


def test_daily_refund_budget_denied():
    assert evaluate_refund("30", Decimal("40"), P).verdict == Verdict.DENY


def test_nan_and_garbage_denied():
    assert evaluate_refund("NaN", Decimal("0"), P).verdict == Verdict.DENY
    assert evaluate_refund("abc", Decimal("0"), P).verdict == Verdict.DENY