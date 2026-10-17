from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from simple_bank.services.transfer_rules import TransferFacts, TransferRulesService

EVALUATED_AT = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


def make_facts(**overrides: object) -> TransferFacts:
    values: dict[str, object] = {
        "source_account_number": "10000001",
        "destination_account_number": "20000002",
        "amount": Decimal("25.00"),
        "source_balance": Decimal("100.00"),
        "customer_outgoing_today": Decimal("0.00"),
        "source_outgoing_today": Decimal("0.00"),
        "source_opened_at": EVALUATED_AT - timedelta(days=30),
        "evaluated_at": EVALUATED_AT,
        "source_active": True,
        "destination_active": True,
    }
    values.update(overrides)
    return TransferFacts(**values)


def evaluate(**overrides: object):
    facts = make_facts(**overrides)
    normalized = replace(
        facts,
        amount=TransferRulesService.normalize_amount(facts.amount),
    )
    return TransferRulesService.evaluate(normalized)


def test_amount_rounding_uses_half_up_to_two_places() -> None:
    assert TransferRulesService.normalize_amount(Decimal("10.005")) == Decimal("10.01")
    assert TransferRulesService.normalize_amount(Decimal("10.004")) == Decimal("10.00")


@pytest.mark.parametrize("amount", [Decimal(0), Decimal(-1), Decimal("0.004")])
def test_non_positive_or_rounded_zero_amount_is_rejected(amount: Decimal) -> None:
    result = evaluate(amount=amount)

    assert result.status == "rejected"
    assert result.error_code == "INVALID_AMOUNT"


def test_rounding_is_applied_before_balance_validation() -> None:
    result = evaluate(amount=Decimal("20.005"), source_balance=Decimal("20.00"))

    assert result.status == "rejected"
    assert result.error_code == "INSUFFICIENT_BALANCE"


def test_exact_available_balance_is_permitted() -> None:
    result = evaluate(amount=Decimal("100.00"), source_balance=Decimal("100.00"))

    assert result.status == "completed"
    assert result.error_code is None


def test_customer_daily_cap_allows_exact_limit_and_rejects_overage() -> None:
    exact_limit = evaluate(
        amount=Decimal("1000.00"),
        source_balance=Decimal("200000.00"),
        customer_outgoing_today=Decimal("99000.00"),
    )
    over_limit = evaluate(
        amount=Decimal("1000.01"),
        source_balance=Decimal("200000.00"),
        customer_outgoing_today=Decimal("99000.00"),
    )

    assert exact_limit.status == "completed"
    assert over_limit.error_code == "DAILY_LIMIT_EXCEEDED"


def test_recent_account_uses_fifty_thousand_cap() -> None:
    account_opened = EVALUATED_AT - timedelta(days=29)
    exact_limit = evaluate(
        amount=Decimal("1000.00"),
        source_balance=Decimal("200000.00"),
        source_outgoing_today=Decimal("49000.00"),
        source_opened_at=account_opened,
    )
    over_limit = evaluate(
        amount=Decimal("0.01"),
        source_balance=Decimal("200000.00"),
        source_outgoing_today=Decimal("50000.00"),
        source_opened_at=account_opened,
    )

    assert exact_limit.status == "completed"
    assert over_limit.error_code == "DAILY_LIMIT_EXCEEDED"


def test_account_just_under_thirty_days_uses_recent_account_cap() -> None:
    result = evaluate(
        amount=Decimal("0.01"),
        source_outgoing_today=Decimal("50000.00"),
        source_opened_at=EVALUATED_AT - timedelta(days=30, microseconds=-1),
    )

    assert result.error_code == "DAILY_LIMIT_EXCEEDED"


def test_account_exactly_thirty_days_old_uses_one_hundred_thousand_cap() -> None:
    result = evaluate(
        amount=Decimal("1000.00"),
        source_balance=Decimal("200000.00"),
        customer_outgoing_today=Decimal("99000.00"),
        source_outgoing_today=Decimal("99000.00"),
        source_opened_at=EVALUATED_AT - timedelta(days=30),
    )

    assert result.status == "completed"


def test_customer_cap_still_applies_when_recent_account_cap_would_allow_transfer() -> None:
    result = evaluate(
        amount=Decimal("1000.00"),
        source_balance=Decimal("200000.00"),
        customer_outgoing_today=Decimal("99500.00"),
        source_outgoing_today=Decimal("49000.00"),
        source_opened_at=EVALUATED_AT - timedelta(days=29),
    )

    assert result.error_code == "DAILY_LIMIT_EXCEEDED"


def test_same_account_transfer_is_rejected() -> None:
    result = evaluate(
        source_account_number="10000001",
        destination_account_number="10000001",
    )

    assert result.error_code == "SAME_AMOUNT"


@pytest.mark.parametrize(
    ("source_active", "destination_active"),
    [(False, True), (True, False)],
)
def test_transfer_with_inactive_account_is_rejected(
    source_active: bool, destination_active: bool
) -> None:
    result = evaluate(source_active=source_active, destination_active=destination_active)

    assert result.error_code == "ACCOUNT_INACTIVE"
