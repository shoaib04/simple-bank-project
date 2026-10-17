from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from simple_bank.services.transfer_service import TransferService

from simple_bank.api.dependencies import get_current_customer_id, get_transfer_service
from simple_bank.db.models import Account
from simple_bank.main import app


@pytest.mark.asyncio
async def test_customer_cannot_debit_another_customers_source_account(
    db_session, seeded_accounts
) -> None:
    await seeded_accounts(db_session)
    app.dependency_overrides[get_current_customer_id] = lambda: "customer-1"
    app.dependency_overrides[get_transfer_service] = lambda: TransferService(db_session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/transfers",
                json={
                    "from_account": "20000002",
                    "to_account": "10000001",
                    "amount": "25.00",
                    "idempotency_key": "ownership-check-001",
                },
            )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()

    sender = await db_session.get(Account, "10000001")
    recipient = await db_session.get(Account, "20000002")
    assert sender.balance == Decimal("100.00")
    assert recipient.balance == Decimal("10.00")
