from decimal import Decimal

import pytest
from simple_bank.schemas.transfers import TransferRequest
from simple_bank.services.transfer_service import TransferService
from sqlalchemy import event, select

from simple_bank.db.models import Account, Transaction


def request(amount: str, key: str) -> TransferRequest:
    return TransferRequest(
        from_account="10000001",
        to_account="20000002",
        amount=amount,
        idempotency_key=key,
    )


@pytest.mark.asyncio
async def test_transfer_posts_rounded_amount_and_both_balances_atomically(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(db_session, sender_balance=Decimal("100.01"))

    outcome = await TransferService(db_session).create_transfer(
        customer_id="customer-1",
        request=request("100.005", "atomic-success"),
    )

    sender = await db_session.get(Account, "10000001")
    recipient = await db_session.get(Account, "20000002")
    transaction = await db_session.get(Transaction, outcome.transaction.transaction_id)
    assert transaction is not None
    assert transaction.status.value == "completed"
    assert transaction.amount == Decimal("100.01")
    assert sender.balance == Decimal("0.00")
    assert recipient.balance == Decimal("110.01")


@pytest.mark.asyncio
async def test_transaction_persistence_failure_rolls_back_both_balance_updates(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(db_session, sender_balance=Decimal("100.01"))

    def fail_transaction_flush(session, flush_context, instances) -> None:
        if any(isinstance(item, Transaction) for item in session.new):
            raise RuntimeError("simulated transaction persistence failure")

    event.listen(db_session.sync_session, "before_flush", fail_transaction_flush)
    try:
        with pytest.raises(RuntimeError, match="simulated transaction persistence failure"):
            await TransferService(db_session).create_transfer(
                customer_id="customer-1",
                request=request("25.00", "atomic-failure"),
            )
    finally:
        event.remove(db_session.sync_session, "before_flush", fail_transaction_flush)
        await db_session.rollback()

    sender = await db_session.get(Account, "10000001")
    recipient = await db_session.get(Account, "20000002")
    assert sender.balance == Decimal("100.01")
    assert recipient.balance == Decimal("10.00")
    transactions = await db_session.scalars(select(Transaction))
    assert list(transactions) == []
