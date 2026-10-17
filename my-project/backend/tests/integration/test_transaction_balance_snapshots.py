import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, event, select, text

from alembic import command
from simple_bank.db.models import Account, Base, Transaction, TransactionStatus
from simple_bank.schemas.transfers import TransferRequest
from simple_bank.services.transfer_service import TransferService


def test_transaction_model_declares_both_balance_snapshots() -> None:
    assert "from_balance_after" in Transaction.__table__.columns
    assert "to_balance_after" in Transaction.__table__.columns


def make_transfer_request(amount: str, key: str) -> TransferRequest:
    return TransferRequest(
        from_account="10000001",
        to_account="20000002",
        amount=amount,
        idempotency_key=key,
    )


@pytest.mark.asyncio
async def test_completed_transfer_persists_both_post_transfer_balances(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(db_session, sender_balance=Decimal("100.01"))

    outcome = await TransferService(db_session).create_transfer(
        customer_id="customer-1",
        request=make_transfer_request("25.00", "snapshot-completed"),
    )

    transaction = await db_session.get(Transaction, outcome.transaction.transaction_id)
    assert transaction.status == TransactionStatus.COMPLETED
    assert transaction.from_balance_after == Decimal("75.01")
    assert transaction.to_balance_after == Decimal("35.00")


@pytest.mark.asyncio
async def test_rejected_transfer_keeps_both_snapshots_null(db_session, seeded_accounts) -> None:
    await seeded_accounts(db_session)

    outcome = await TransferService(db_session).create_transfer(
        customer_id="customer-1",
        request=make_transfer_request("0.00", "snapshot-rejected"),
    )

    transaction = await db_session.get(Transaction, outcome.transaction.transaction_id)
    assert transaction.status == TransactionStatus.REJECTED
    assert transaction.from_balance_after is None
    assert transaction.to_balance_after is None


@pytest.mark.asyncio
async def test_snapshot_write_failure_rolls_back_transfer_balances(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(db_session, sender_balance=Decimal("100.01"))

    def fail_transaction_flush(session, flush_context, instances) -> None:
        if any(isinstance(item, Transaction) for item in session.new):
            raise RuntimeError("simulated transaction snapshot persistence failure")

    event.listen(db_session.sync_session, "before_flush", fail_transaction_flush)
    try:
        with pytest.raises(RuntimeError, match="simulated transaction snapshot persistence failure"):
            await TransferService(db_session).create_transfer(
                customer_id="customer-1",
                request=make_transfer_request("25.00", "snapshot-rollback"),
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


def test_legacy_migration_backfills_transfer_sides_and_rejected_rows(monkeypatch) -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL migration tests")
    from sqlalchemy.engine import make_url

    parsed_url = make_url(database_url)
    if not parsed_url.database or "test" not in parsed_url.database.lower():
        pytest.fail("TEST_DATABASE_URL must point to a dedicated database with 'test' in its name")

    project_root = Path(__file__).resolve().parents[2]
    migration_config = Config(str(project_root / "alembic.ini"))
    monkeypatch.setenv("DATABASE_URL", database_url)
    engine = create_engine(database_url)
    first_time = datetime(2026, 10, 17, 10, 0, tzinfo=UTC)
    second_time = first_time + timedelta(minutes=1)
    first_id = UUID("00000000-0000-0000-0000-000000000001")
    second_id = UUID("00000000-0000-0000-0000-000000000002")
    rejected_id = UUID("00000000-0000-0000-0000-000000000003")

    try:
        Base.metadata.drop_all(engine)
        command.upgrade(migration_config, "0001_transfer_schema")
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO customers (customer_id) VALUES ('customer-1'), ('customer-2')")
            )
            connection.execute(
                text(
                    "INSERT INTO accounts "
                    "(account_number, customer_id, opened_at, balance, status) VALUES "
                    "('10000001', 'customer-1', :opened_at, 95.00, 'active'), "
                    "('20000002', 'customer-2', :opened_at, 15.00, 'active')"
                ),
                {"opened_at": first_time},
            )
            connection.execute(
                text(
                    "INSERT INTO transactions "
                    "(transaction_id, from_account, to_account, amount, status, created_at, "
                    "customer_id, idempotency_key, error_code) VALUES "
                    "(:first_id, '10000001', '20000002', 10.00, 'completed', :first_time, "
                    "'customer-1', 'legacy-1', NULL), "
                    "(:second_id, '20000002', '10000001', 5.00, 'completed', :second_time, "
                    "'customer-2', 'legacy-2', NULL), "
                    "(:rejected_id, '10000001', '20000002', 0.00, 'rejected', :second_time, "
                    "'customer-1', 'legacy-rejected', 'INVALID_AMOUNT')"
                ),
                {
                    "first_id": first_id,
                    "second_id": second_id,
                    "rejected_id": rejected_id,
                    "first_time": first_time,
                    "second_time": second_time,
                },
            )

        command.upgrade(migration_config, "head")
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT transaction_id, from_balance_after, to_balance_after "
                    "FROM transactions ORDER BY created_at, transaction_id"
                )
            ).mappings().all()

        snapshots = {row["transaction_id"]: row for row in rows}
        assert snapshots[first_id]["from_balance_after"] == Decimal("90.00")
        assert snapshots[first_id]["to_balance_after"] == Decimal("20.00")
        assert snapshots[second_id]["from_balance_after"] == Decimal("15.00")
        assert snapshots[second_id]["to_balance_after"] == Decimal("95.00")
        assert snapshots[rejected_id]["from_balance_after"] is None
        assert snapshots[rejected_id]["to_balance_after"] is None
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
