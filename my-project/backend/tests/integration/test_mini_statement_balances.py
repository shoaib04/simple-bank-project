from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from simple_bank.db.models import Transaction, TransactionStatus
from simple_bank.services.mini_statement_service import MiniStatementService


@pytest.mark.asyncio
async def test_both_account_sides_keep_historical_balances_after_later_transfer(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(
        db_session,
        sender_balance=Decimal("65.00"),
        recipient_balance=Decimal("45.00"),
    )
    first_time = datetime.now(UTC) - timedelta(minutes=1)
    second_time = datetime.now(UTC)
    db_session.add_all(
        [
            Transaction(
                transaction_id=UUID(int=3001),
                from_account="10000001",
                to_account="20000002",
                amount=Decimal("25.00"),
                status=TransactionStatus.COMPLETED,
                created_at=first_time,
                customer_id="customer-1",
                idempotency_key="balance-first",
                from_balance_after=Decimal("75.00"),
                to_balance_after=Decimal("35.00"),
            ),
            Transaction(
                transaction_id=UUID(int=3002),
                from_account="10000001",
                to_account="20000002",
                amount=Decimal("10.00"),
                status=TransactionStatus.COMPLETED,
                created_at=second_time,
                customer_id="customer-1",
                idempotency_key="balance-second",
                from_balance_after=Decimal("65.00"),
                to_balance_after=Decimal("45.00"),
            ),
        ]
    )
    await db_session.commit()

    service = MiniStatementService(db_session)
    source_statement = await service.get_statement("customer-1", "10000001")
    destination_statement = await service.get_statement("customer-2", "20000002")

    assert [entry.debit for entry in source_statement.transactions] == ["10.00", "25.00"]
    assert [entry.credit for entry in source_statement.transactions] == ["0.00", "0.00"]
    assert [entry.balance_after for entry in source_statement.transactions] == ["65.00", "75.00"]
    assert [entry.debit for entry in destination_statement.transactions] == ["0.00", "0.00"]
    assert [entry.credit for entry in destination_statement.transactions] == ["10.00", "25.00"]
    assert [entry.balance_after for entry in destination_statement.transactions] == ["45.00", "35.00"]
    assert all(entry.amount in {"10.00", "25.00"} for entry in source_statement.transactions)
