from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

CENT = Decimal("0.01")
CUSTOMER_DAILY_LIMIT = Decimal("100000.00")
RECENT_ACCOUNT_DAILY_LIMIT = Decimal("50000.00")
MATURE_ACCOUNT_DAILY_LIMIT = Decimal("100000.00")
RECENT_ACCOUNT_AGE = timedelta(days=30)


@dataclass(frozen=True)
class TransferFacts:
    source_account_number: str
    destination_account_number: str
    amount: Decimal
    source_balance: Decimal
    customer_outgoing_today: Decimal
    source_outgoing_today: Decimal
    source_opened_at: datetime
    evaluated_at: datetime
    source_active: bool
    destination_active: bool


@dataclass(frozen=True)
class TransferDecision:
    status: Literal["completed", "rejected"]
    error_code: str | None = None


class TransferRulesService:
    @staticmethod
    def normalize_amount(amount: Decimal) -> Decimal:
        if not isinstance(amount, Decimal):
            raise TypeError("Transfer amounts must use Decimal")
        if not amount.is_finite():
            raise ValueError("Transfer amounts must be finite decimals")
        return amount.quantize(CENT, rounding=ROUND_HALF_UP)

    @classmethod
    def evaluate(cls, facts: TransferFacts) -> TransferDecision:
        amount = facts.amount
        if amount <= 0:
            return TransferDecision("rejected", "INVALID_AMOUNT")
        if amount > facts.source_balance:
            return TransferDecision("rejected", "INSUFFICIENT_BALANCE")
        if facts.customer_outgoing_today + amount > CUSTOMER_DAILY_LIMIT:
            return TransferDecision("rejected", "DAILY_LIMIT_EXCEEDED")

        opened_at = cls._as_utc(facts.source_opened_at)
        evaluated_at = cls._as_utc(facts.evaluated_at)
        account_limit = (
            RECENT_ACCOUNT_DAILY_LIMIT
            if evaluated_at - opened_at < RECENT_ACCOUNT_AGE
            else MATURE_ACCOUNT_DAILY_LIMIT
        )
        if facts.source_outgoing_today + amount > account_limit:
            return TransferDecision("rejected", "DAILY_LIMIT_EXCEEDED")
        if facts.source_account_number == facts.destination_account_number:
            return TransferDecision("rejected", "SAME_AMOUNT")
        if not facts.source_active or not facts.destination_active:
            return TransferDecision("rejected", "ACCOUNT_INACTIVE")
        return TransferDecision("completed")

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Transfer evaluation timestamps must be timezone-aware")
        return value.astimezone(UTC)
