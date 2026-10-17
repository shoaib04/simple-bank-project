import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from simple_bank.db.models import Account, AccountStatus, Base, Customer


@pytest_asyncio.fixture
async def db_session_factory() -> async_sessionmaker[AsyncSession]:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests")
    parsed_url = make_url(database_url)
    if not parsed_url.database or "test" not in parsed_url.database.lower():
        pytest.fail("TEST_DATABASE_URL must point to a dedicated database with 'test' in its name")

    engine = create_async_engine(database_url, pool_pre_ping=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield session_factory
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_session_factory: async_sessionmaker[AsyncSession]) -> AsyncSession:
    async with db_session_factory() as session:
        yield session
        await session.rollback()


async def seed_transfer_accounts(
    session: AsyncSession,
    sender_balance: Decimal = Decimal("100.00"),
    recipient_balance: Decimal = Decimal("10.00"),
    sender_opened_at: datetime | None = None,
) -> None:
    opened_at = sender_opened_at or datetime.now(UTC) - timedelta(days=30)
    sender_customer = Customer(customer_id="customer-1")
    recipient_customer = Customer(customer_id="customer-2")
    sender = Account(
        account_number="10000001",
        customer=sender_customer,
        opened_at=opened_at,
        balance=sender_balance,
        status=AccountStatus.ACTIVE,
    )
    recipient = Account(
        account_number="20000002",
        customer=recipient_customer,
        opened_at=opened_at,
        balance=recipient_balance,
        status=AccountStatus.ACTIVE,
    )
    session.add_all([sender_customer, recipient_customer, sender, recipient])
    await session.commit()


@pytest.fixture

def seeded_accounts():
    return seed_transfer_accounts
