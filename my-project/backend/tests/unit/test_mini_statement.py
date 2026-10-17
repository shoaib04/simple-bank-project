from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from simple_bank.db.models import Transaction, TransactionStatus
from simple_bank.services.mini_statement_service import MiniStatementService


def make_transaction(**overrides: object) -> Transaction:
    values: dict[str, object] = {
        "transaction_id": uuid4(),
        "from_account": "1234567890121001",
        "to_account": "9876543210982002",
        "amount": Decimal("125.50"),
        "status": TransactionStatus.COMPLETED,
        "created_at": datetime(
            2026, 10, 17, 14, 0, tzinfo=timezone(timedelta(hours=2))
        ),
        "customer_id": "customer-1",
        "idempotency_key": "mini-statement-unit",
        "from_balance_after": Decimal("874.50"),
        "to_balance_after": Decimal("225.50"),
    }
    values.update(overrides)
    return Transaction(**values)


def test_outgoing_entry_uses_source_snapshot_and_masks_counterparty() -> None:
    transaction = make_transaction()

    entry = MiniStatementService._to_entry(transaction, "1234567890121001")

    assert entry.date == datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
    assert entry.description == "Transfer to XXXX2002"
    assert entry.debit == "125.50"
    assert entry.credit == "0.00"
    assert entry.amount == "125.50"
    assert entry.balance_after == "874.50"


def test_incoming_entry_uses_destination_snapshot_and_masks_counterparty() -> None:
    transaction = make_transaction(created_at=datetime(2026, 10, 17, 12, 0, tzinfo=UTC))

    entry = MiniStatementService._to_entry(transaction, "9876543210982002")

    assert entry.description == "Transfer from XXXX1001"
    assert entry.debit == "0.00"
    assert entry.credit == "125.50"
    assert entry.amount == "125.50"
    assert entry.balance_after == "225.50"


def test_completed_transaction_without_snapshot_is_rejected() -> None:
    transaction = make_transaction(from_balance_after=None)

    with pytest.raises(RuntimeError, match="missing its balance snapshot"):
        MiniStatementService._to_entry(transaction, "1234567890121001")
