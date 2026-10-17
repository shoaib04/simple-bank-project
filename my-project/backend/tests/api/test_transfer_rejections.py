from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from simple_bank.api.dependencies import get_current_customer_id, get_transfer_service
from simple_bank.db.models import Transaction, TransactionStatus, TransferErrorCode
from simple_bank.main import app
from simple_bank.services.transfer_service import TransferOutcome

REJECTION_MESSAGES = {
    "INVALID_AMOUNT": "Enter an amount greater than Rs 0.",
    "INSUFFICIENT_BALANCE": "The source account does not have enough balance.",
    "DAILY_LIMIT_EXCEEDED": "The daily transfer limit has been reached.",
    "SAME_AMOUNT": "Choose a destination account different from the source.",
    "ACCOUNT_INACTIVE": "Both accounts must be active to transfer funds.",
}


@pytest.mark.parametrize(
    "error_code",
    [
        "INVALID_AMOUNT",
        "INSUFFICIENT_BALANCE",
        "DAILY_LIMIT_EXCEEDED",
        "SAME_AMOUNT",
        "ACCOUNT_INACTIVE",
    ],
)
@pytest.mark.asyncio
async def test_each_business_rejection_returns_saved_outcome(error_code: str) -> None:
    transaction_id = uuid4()

    class RejectedTransferService:
        async def create_transfer(self, customer_id: str, request: object) -> TransferOutcome:
            transaction = Transaction(
                transaction_id=transaction_id,
                from_account=request.from_account,
                to_account=request.to_account,
                amount=request.amount,
                status=TransactionStatus.REJECTED,
                created_at=datetime.now(UTC),
                customer_id=customer_id,
                idempotency_key=request.idempotency_key,
                error_code=TransferErrorCode(error_code),
            )
            return TransferOutcome(
                transaction=transaction,
                message=f"Transfer rejected: {error_code}.",
            )

    app.dependency_overrides[get_current_customer_id] = lambda: "customer-1"
    app.dependency_overrides[get_transfer_service] = RejectedTransferService
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/transfers",
                json={
                    "from_account": "10000001",
                    "to_account": "20000002",
                    "amount": "0.00",
                    "idempotency_key": "rejection-001",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["status"] == "rejected"
    assert response.json()["transaction_id"] == str(transaction_id)
    assert response.json()["error_code"] == error_code
    assert response.json()["message"] == REJECTION_MESSAGES[error_code]
