import asyncio
from decimal import Decimal
from time import perf_counter

import pytest
from httpx import ASGITransport, AsyncClient

from simple_bank.api.dependencies import get_current_customer_id, get_transfer_service
from simple_bank.main import app
from simple_bank.services.transfer_service import TransferService


@pytest.mark.asyncio
async def test_one_hundred_concurrent_transfer_responses_arrive_within_one_second(
    db_session, db_session_factory, seeded_accounts
) -> None:
    await seeded_accounts(db_session, sender_balance=Decimal("100000.00"))
    app.dependency_overrides[get_current_customer_id] = lambda: "customer-1"

    async def transfer_service_override():
        async with db_session_factory() as session:
            yield TransferService(session)

    app.dependency_overrides[get_transfer_service] = transfer_service_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            async def submit(index: int):
                started_at = perf_counter()
                response = await client.post(
                    "/api/v1/transfers",
                    json={
                        "from_account": "10000001",
                        "to_account": "20000002",
                        "amount": "1000.00",
                        "idempotency_key": f"latency-{index}",
                    },
                )
                return response, perf_counter() - started_at

            results = await asyncio.gather(*(submit(index) for index in range(100)))
    finally:
        app.dependency_overrides.clear()

    assert all(response.status_code == 201 for response, _ in results)
    assert len(results) == 100
    assert all(elapsed < 1.0 for _, elapsed in results)
