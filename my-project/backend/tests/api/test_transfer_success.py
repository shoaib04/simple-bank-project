from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from simple_bank.api.dependencies import get_current_customer_id, get_transfer_service
from simple_bank.db.models import Transaction, TransactionStatus
from simple_bank.main import app
from simple_bank.services.transfer_service import TransferOutcome


class SuccessfulTransferService:
    async def create_transfer(self, customer_id: str, request: object) -> TransferOutcome:
        assert customer_id == "customer-1"
        assert request.from_account == "10000001"
        assert request.to_account == "20000002"
        assert request.amount == Decimal("25.00")
        assert request.idempotency_key == "request-001"
        return TransferOutcome(
            transaction=Transaction(
                transaction_id=UUID("4de58d6c-840b-47eb-a2de-1950eaa1c113"),
                from_account=request.from_account,
                to_account=request.to_account,
                amount=request.amount,
                status=TransactionStatus.COMPLETED,
                created_at=datetime(2026, 10, 17, 12, 0, tzinfo=UTC),
                customer_id=customer_id,
                idempotency_key=request.idempotency_key,
            ),
            message="Transfer completed.",
        )


@pytest.mark.asyncio
async def test_successful_transfer_response_matches_contract() -> None:
    app.dependency_overrides[get_current_customer_id] = lambda: "customer-1"
    app.dependency_overrides[get_transfer_service] = SuccessfulTransferService
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/transfers",
                json={
                    "from_account": "10000001",
                    "to_account": "20000002",
                    "amount": "25.00",
                    "idempotency_key": "request-001",
                },
            )

        assert response.status_code == 201
        body = response.json()
        UUID(body["transaction_id"])
        assert body["from_account"] == "XXXX0001"
        assert body["to_account"] == "XXXX0002"
        assert body["amount"] == "25.00"
        assert body["status"] == "completed"
        assert body["error_code"] is None
        assert body["message"] == "Transfer completed."
    finally:
        app.dependency_overrides.clear()
