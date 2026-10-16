from decimal import Decimal

import pytest

from awg.policy import Policy
from awg.policy_nl import policy_from_data

BASE = Policy()


def test_valid_data():
    p = policy_from_data(
        {"max_per_tx": 80, "daily_budget": 200, "approval_threshold": 30,
         "allowed_recipients": []}, BASE)
    assert p.max_per_tx == Decimal("80") and p.approval_threshold == Decimal("30")


def test_null_keeps_base_value():
    p = policy_from_data({"daily_budget": 300}, BASE)
    assert p.daily_budget == Decimal("300") and p.max_per_tx == BASE.max_per_tx


def test_negative_rejected():
    with pytest.raises(ValueError):
        policy_from_data({"max_per_tx": -5}, BASE)


def test_inconsistent_rejected():
    with pytest.raises(ValueError):
        policy_from_data({"approval_threshold": 400}, BASE)


def test_bad_recipient_rejected():
    with pytest.raises(ValueError):
        policy_from_data({"allowed_recipients": ["not-an-email"]}, BASE)