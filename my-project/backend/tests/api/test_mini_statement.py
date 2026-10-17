from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from simple_bank.api.dependencies import get_current_customer_id, get_mini_statement_service
from simple_bank.main import app
from simple_bank.schemas.mini_statement import MiniStatementEntry, MiniStatementResponse

ACCOUNT_NUMBER = "1234567890121234"


def sample_statement(entries: list[MiniStatementEntry] | None = None) -> MiniStatementResponse:
    return MiniStatementResponse(
        account_number="XXXX1234",
        transactions=(
            entries
            if entries is not None
            else [
                MiniStatementEntry(
                    date=datetime(2026, 10, 17, 12, 0, tzinfo=UTC),
                    description="Transfer to XXXX5678",
                    debit="125.50",
                    credit="0.00",
                    amount="125.50",
                    balance_after="874.50",
                )
            ]
        ),
    )


class StubMiniStatementService:
    def __init__(self, response: MiniStatementResponse | None) -> None:
        self.response = response

    async def get_statement(self, customer_id: str, account_number: str):
        assert customer_id == "customer-1"
        assert account_number == ACCOUNT_NUMBER
        return self.response


@pytest.mark.asyncio
async def test_owned_account_returns_masked_statement() -> None:
    app.dependency_overrides[get_current_customer_id] = lambda: "customer-1"
    app.dependency_overrides[get_mini_statement_service] = lambda: StubMiniStatementService(
        sample_statement()
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/api/v1/accounts/{ACCOUNT_NUMBER}/mini-statement"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["account_number"] == "XXXX1234"
    assert ACCOUNT_NUMBER not in response.text
    assert len(body["transactions"]) == 1
    assert body["transactions"][0] == {
        "date": "2026-10-17T12:00:00Z",
        "description": "Transfer to XXXX5678",
        "debit": "125.50",
        "credit": "0.00",
        "amount": "125.50",
        "balance_after": "874.50",
    }


@pytest.mark.asyncio
async def test_owned_account_with_no_activity_returns_empty_list() -> None:
    app.dependency_overrides[get_current_customer_id] = lambda: "customer-1"
    app.dependency_overrides[get_mini_statement_service] = lambda: StubMiniStatementService(
        sample_statement([])
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/api/v1/accounts/{ACCOUNT_NUMBER}/mini-statement"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"account_number": "XXXX1234", "transactions": []}


@pytest.mark.asyncio
async def test_missing_or_non_owned_account_returns_not_found_without_data() -> None:
    app.dependency_overrides[get_current_customer_id] = lambda: "customer-1"
    app.dependency_overrides[get_mini_statement_service] = lambda: StubMiniStatementService(
        None
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/api/v1/accounts/{ACCOUNT_NUMBER}/mini-statement"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert ACCOUNT_NUMBER not in response.text
    assert "transactions" not in response.json()


@pytest.mark.asyncio
async def test_request_without_trusted_customer_context_returns_unauthorized() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/v1/accounts/{ACCOUNT_NUMBER}/mini-statement"
        )

    assert response.status_code == 401
    assert ACCOUNT_NUMBER not in response.text
