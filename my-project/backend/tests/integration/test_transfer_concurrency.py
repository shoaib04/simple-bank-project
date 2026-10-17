import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from simple_bank.api.dependencies import get_current_customer_id, get_transfer_service
from simple_bank.db.models import Account, AccountStatus, Transaction
from simple_bank.main import app
from simple_bank.services.transfer_service import TransferService


@pytest.mark.asyncio
async def test_one_hundred_concurrent_transfers_preserve_both_daily_caps(
    db_session, db_session_factory, seeded_accounts
) -> None:
    recent_opening = datetime.now(UTC) - timedelta(days=29)
    await seeded_accounts(
        db_session,
        sender_balance=Decimal("100000.00"),
        sender_opened_at=recent_opening,
    )
    mature_sender = Account(
        account_number="30000003",
        customer_id="customer-2",
        opened_at=datetime.now(UTC) - timedelta(days=45),
        balance=Decimal("100000.00"),
        status=AccountStatus.ACTIVE,
    )
    db_session.add(mature_sender)
    await db_session.commit()

    app.dependency_overrides[get_current_customer_id] = lambda request: request.headers[
        "x-test-customer"
    ]

    async def transfer_service_override():
        async with db_session_factory() as session:
            yield TransferService(session)

    app.dependency_overrides[get_transfer_service] = transfer_service_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            recent_requests = [
                client.post(
                    "/api/v1/transfers",
                    json={
                        "from_account": "10000001",
                        "to_account": "20000002",
                        "amount": "1000.00",
                        "idempotency_key": f"recent-{index}",
                    },
                    headers={"x-test-customer": "customer-1"},
                )
                for index in range(60)
            ]
            mature_requests = [
                client.post(
                    "/api/v1/transfers",
                    json={
                        "from_account": "30000003",
                        "to_account": "20000002",
                        "amount": "1000.00",
                        "idempotency_key": f"mature-{index}",
                    },
                    headers={"x-test-customer": "customer-2"},
                )
                for index in range(40)
            ]
            responses = await asyncio.gather(*(recent_requests + mature_requests))
    finally:
        app.dependency_overrides.clear()

    response_bodies = [response.json() for response in responses]
    assert all(response.status_code == 201 for response in responses)
    assert sum(body["status"] == "completed" for body in response_bodies) == 90
    assert sum(body["status"] == "rejected" for body in response_bodies) == 10
    assert all(
        body["error_code"] == "DAILY_LIMIT_EXCEEDED"
        for body in response_bodies
        if body["status"] == "rejected"
    )
    assert len({body["transaction_id"] for body in response_bodies}) == 100

    async with db_session_factory() as verification_session:
        recent_sender = await verification_session.get(Account, "10000001")
        mature_sender = await verification_session.get(Account, "30000003")
        recipient = await verification_session.get(Account, "20000002")
        transactions = await verification_session.scalars(select(Transaction))
        assert recent_sender.balance == Decimal("50000.00")
        assert mature_sender.balance == Decimal("60000.00")
        assert recipient.balance == Decimal("90010.00")
        assert len(list(transactions)) == 100
