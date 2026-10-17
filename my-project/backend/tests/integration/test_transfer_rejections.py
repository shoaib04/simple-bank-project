from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from simple_bank.db.models import (
    Account,
    AccountStatus,
    Transaction,
    TransactionStatus,
    TransferErrorCode,
)
from simple_bank.schemas.transfers import TransferRequest
from simple_bank.services.transfer_service import TransferService


def make_request(amount: str, key: str, to_account: str = "20000002") -> TransferRequest:
    return TransferRequest(
        from_account="10000001",
        to_account=to_account,
        amount=amount,
        idempotency_key=key,
    )


async def assert_saved_rejection(session, request: TransferRequest, expected_code: str) -> None:
    before_sender = await session.get(Account, request.from_account)
    before_recipient = await session.get(Account, request.to_account)
    sender_balance = before_sender.balance
    recipient_balance = before_recipient.balance

    outcome = await TransferService(session).create_transfer(
        customer_id="customer-1",
        request=request,
    )

    assert outcome.transaction.status == TransactionStatus.REJECTED
    assert outcome.transaction.error_code == TransferErrorCode(expected_code)
    sender = await session.get(Account, request.from_account)
    recipient = await session.get(Account, request.to_account)
    assert sender.balance == sender_balance
    assert recipient.balance == recipient_balance
    persisted = await session.scalar(
        select(Transaction).where(Transaction.idempotency_key == request.idempotency_key)
    )
    assert persisted is not None
    assert persisted.transaction_id == outcome.transaction.transaction_id


@pytest.mark.asyncio
async def test_invalid_amount_is_saved_without_balance_changes(db_session, seeded_accounts) -> None:
    await seeded_accounts(db_session)
    await assert_saved_rejection(db_session, make_request("0.00", "invalid-amount"), "INVALID_AMOUNT")


@pytest.mark.asyncio
async def test_insufficient_balance_is_saved_without_balance_changes(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(db_session)
    await assert_saved_rejection(
        db_session,
        make_request("101.00", "insufficient"),
        "INSUFFICIENT_BALANCE",
    )


@pytest.mark.asyncio
async def test_same_account_is_saved_as_rejection(db_session, seeded_accounts) -> None:
    await seeded_accounts(db_session)
    await assert_saved_rejection(
        db_session,
        make_request("25.00", "same-account", to_account="10000001"),
        "SAME_AMOUNT",
    )


@pytest.mark.asyncio
async def test_inactive_recipient_is_saved_without_balance_changes(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(db_session)
    recipient = await db_session.get(Account, "20000002")
    recipient.status = AccountStatus.INACTIVE
    await db_session.commit()

    await assert_saved_rejection(
        db_session,
        make_request("25.00", "inactive-recipient"),
        "ACCOUNT_INACTIVE",
    )


@pytest.mark.asyncio
async def test_customer_daily_limit_rejection_is_saved_without_balance_changes(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(db_session, sender_balance=Decimal("200000.00"))
    customer_account = Account(
        account_number="30000003",
        customer_id="customer-1",
        opened_at=datetime.now(UTC) - timedelta(days=45),
        balance=Decimal("200000.00"),
        status=AccountStatus.ACTIVE,
    )
    history = Transaction(
        transaction_id=uuid4(),
        from_account="30000003",
        to_account="20000002",
        amount=Decimal("99500.00"),
        status=TransactionStatus.COMPLETED,
        created_at=datetime.now(UTC),
        customer_id="customer-1",
        idempotency_key="prior-customer-transfer",
    )
    db_session.add_all([customer_account, history])
    await db_session.commit()

    await assert_saved_rejection(
        db_session,
        make_request("1000.01", "customer-limit"),
        "DAILY_LIMIT_EXCEEDED",
    )


@pytest.mark.asyncio
async def test_recent_source_account_daily_limit_rejection_is_saved(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(
        db_session,
        sender_balance=Decimal("200000.00"),
        sender_opened_at=datetime.now(UTC) - timedelta(days=29),
    )
    prior_transfer = Transaction(
        transaction_id=uuid4(),
        from_account="10000001",
        to_account="20000002",
        amount=Decimal("50000.00"),
        status=TransactionStatus.COMPLETED,
        created_at=datetime.now(UTC),
        customer_id="customer-1",
        idempotency_key="prior-source-transfer",
    )
    db_session.add(prior_transfer)
    await db_session.commit()

    await assert_saved_rejection(
        db_session,
        make_request("0.01", "source-account-limit"),
        "DAILY_LIMIT_EXCEEDED",
    )
