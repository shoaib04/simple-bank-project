from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from simple_bank.services.transfer_service import TransferService

from simple_bank.api.dependencies import get_current_customer_id, get_transfer_service
from simple_bank.db.models import Account
from simple_bank.main import app

TRANSFER_REQUEST = {
    "from_account": "10000001",
    "to_account": "20000002",
    "amount": "25.00",
    "idempotency_key": "request-idempotent-001",
}


def configure_transfer_app(db_session) -> None:
    app.dependency_overrides[get_current_customer_id] = lambda: "customer-1"
    app.dependency_overrides[get_transfer_service] = lambda: TransferService(db_session)


@pytest.mark.asyncio
async def test_retry_replays_result_but_new_key_creates_new_transfer(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(db_session)
    configure_transfer_app(db_session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await client.post("/api/v1/transfers", json=TRANSFER_REQUEST)
            retry = await client.post("/api/v1/transfers", json=TRANSFER_REQUEST)
            separately_initiated = await client.post(
                "/api/v1/transfers",
                json={**TRANSFER_REQUEST, "idempotency_key": "request-idempotent-002"},
            )

        assert first.status_code == 201
        assert retry.status_code == 200
        assert first.json()["transaction_id"] == retry.json()["transaction_id"]
        assert separately_initiated.status_code == 201
        assert separately_initiated.json()["transaction_id"] != first.json()["transaction_id"]
    finally:
        app.dependency_overrides.clear()

    sender = await db_session.get(Account, "10000001")
    recipient = await db_session.get(Account, "20000002")
    assert sender.balance == Decimal("50.00")
    assert recipient.balance == Decimal("60.00")


@pytest.mark.asyncio
async def test_reusing_idempotency_key_with_different_payload_returns_conflict(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(db_session)
    configure_transfer_app(db_session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await client.post("/api/v1/transfers", json=TRANSFER_REQUEST)
            conflict = await client.post(
                "/api/v1/transfers",
                json={**TRANSFER_REQUEST, "amount": "30.00"},
            )

        assert first.status_code == 201
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    finally:
        app.dependency_overrides.clear()

    sender = await db_session.get(Account, "10000001")
    recipient = await db_session.get(Account, "20000002")
    assert sender.balance == Decimal("75.00")
    assert recipient.balance == Decimal("35.00")
