from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from simple_bank.api.dependencies import get_current_customer_id, get_transfer_service
from simple_bank.db.models import Transaction, TransactionStatus, TransferErrorCode
from simple_bank.main import app
from simple_bank.services.transfer_service import TransferOutcome


@pytest.mark.parametrize("completed", [True, False])
@pytest.mark.asyncio
async def test_transfer_response_masks_both_account_numbers(completed: bool) -> None:
    source_number = "1234567890121001"
    recipient_number = "9876543210982002"
    transaction = Transaction(
        transaction_id=uuid4(),
        from_account=source_number,
        to_account=recipient_number,
        amount=Decimal("25.00"),
        status=(TransactionStatus.COMPLETED if completed else TransactionStatus.REJECTED),
        created_at=datetime.now(UTC),
        customer_id="customer-1",
        idempotency_key="masking-001",
        error_code=(None if completed else TransferErrorCode.ACCOUNT_INACTIVE),
    )

    class TransferResultService:
        async def create_transfer(self, customer_id: str, request: object) -> TransferOutcome:
            return TransferOutcome(
                transaction=transaction,
                message="Transfer completed." if completed else "Both accounts must be active.",
            )

    app.dependency_overrides[get_current_customer_id] = lambda: "customer-1"
    app.dependency_overrides[get_transfer_service] = TransferResultService
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/transfers",
                json={
                    "from_account": source_number,
                    "to_account": recipient_number,
                    "amount": "25.00",
                    "idempotency_key": "masking-001",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["from_account"] == "XXXX1001"
    assert body["to_account"] == "XXXX2002"
    assert source_number not in response.text
    assert recipient_number not in response.text
