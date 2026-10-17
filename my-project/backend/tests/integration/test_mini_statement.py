from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from simple_bank.services.mini_statement_service import MiniStatementService
from sqlalchemy import select

from simple_bank.db.models import (
    Account,
    AccountStatus,
    Transaction,
    TransactionStatus,
    TransferErrorCode,
)


async def add_statement_history(session, seeded_accounts) -> None:
    await seeded_accounts(
        session,
        sender_balance=Decimal("88.00"),
        recipient_balance=Decimal("22.00"),
    )
    start = datetime.now(UTC) - timedelta(minutes=12)
    transactions = []
    for index in range(1, 13):
        created_at = start + timedelta(minutes=index)
        if index == 11:
            created_at = start + timedelta(minutes=12)
        if index == 12:
            created_at = start + timedelta(minutes=12)
        transactions.append(
            Transaction(
                transaction_id=UUID(int=1000 + index),
                from_account="10000001",
                to_account="20000002",
                amount=Decimal(f"{index}.00"),
                status=TransactionStatus.COMPLETED,
                created_at=created_at,
                customer_id="customer-1",
                idempotency_key=f"history-{index}",
                from_balance_after=Decimal(f"{100 - index}.00"),
                to_balance_after=Decimal(f"{10 + index}.00"),
            )
        )
    transactions.append(
        Transaction(
            transaction_id=UUID(int=2000),
            from_account="10000001",
            to_account="20000002",
            amount=Decimal("0.00"),
            status=TransactionStatus.REJECTED,
            created_at=start + timedelta(minutes=13),
            customer_id="customer-1",
            idempotency_key="history-rejected",
            error_code=TransferErrorCode.INVALID_AMOUNT,
        )
    )
    session.add_all(transactions)
    await session.commit()


@pytest.mark.asyncio
async def test_returns_ten_newest_completed_entries_and_does_not_mutate_account(
    db_session, seeded_accounts
) -> None:
    await add_statement_history(db_session, seeded_accounts)

    statement = await MiniStatementService(db_session).get_statement(
        customer_id="customer-1",
        account_number="10000001",
    )

    assert statement.account_number == "XXXX0001"
    assert [entry.amount for entry in statement.transactions] == [
        f"{amount}.00" for amount in range(12, 2, -1)
    ]
    assert statement.transactions[0].balance_after == "88.00"
    assert statement.transactions[1].balance_after == "89.00"
    assert len(statement.transactions) == 10

    sender = await db_session.get(Account, "10000001")
    recipient = await db_session.get(Account, "20000002")
    assert sender.balance == Decimal("88.00")
    assert recipient.balance == Decimal("22.00")
    transactions = await db_session.scalars(select(Transaction))
    assert len(list(transactions)) == 13


@pytest.mark.asyncio
async def test_inactive_owned_account_can_read_empty_statement(db_session, seeded_accounts) -> None:
    await seeded_accounts(db_session)
    sender = await db_session.get(Account, "10000001")
    sender.status = AccountStatus.INACTIVE
    await db_session.commit()

    statement = await MiniStatementService(db_session).get_statement(
        customer_id="customer-1",
        account_number="10000001",
    )

    assert statement.account_number == "XXXX0001"
    assert statement.transactions == []
