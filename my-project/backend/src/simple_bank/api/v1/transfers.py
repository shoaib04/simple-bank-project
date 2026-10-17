from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from simple_bank.api.dependencies import get_current_customer_id, get_transfer_service
from simple_bank.schemas.transfers import ApiError, TransferRequest, TransferResponse
from simple_bank.security.account_masking import mask_account_number
from simple_bank.services.transfer_service import (
    AccountNotFoundError,
    IdempotencyKeyConflictError,
    SourceAccountForbiddenError,
    TransferService,
)

router = APIRouter()
REJECTION_MESSAGES = {
    "INVALID_AMOUNT": "Enter an amount greater than Rs 0.",
    "INSUFFICIENT_BALANCE": "The source account does not have enough balance.",
    "DAILY_LIMIT_EXCEEDED": "The daily transfer limit has been reached.",
    "SAME_AMOUNT": "Choose a destination account different from the source.",
    "ACCOUNT_INACTIVE": "Both accounts must be active to transfer funds.",
}


@router.post(
    "/transfers",
    response_model=TransferResponse,
    status_code=201,
    responses={
        200: {"model": TransferResponse, "description": "Original result returned for a retry."},
        403: {"model": ApiError, "description": "Source account ownership is forbidden."},
        404: {"model": ApiError, "description": "A transfer account does not exist."},
        409: {"model": ApiError, "description": "Idempotency key conflicts with a prior request."},
        422: {"model": ApiError, "description": "Malformed transfer request."},
    },
)
async def create_transfer(
    request: TransferRequest,
    customer_id: Annotated[str, Depends(get_current_customer_id)],
    service: Annotated[TransferService, Depends(get_transfer_service)],
) -> JSONResponse:
    try:
        outcome = await service.create_transfer(customer_id=customer_id, request=request)
    except SourceAccountForbiddenError:
        error = ApiError(
            code="FORBIDDEN",
            message="The authenticated customer cannot debit this source account.",
        )
        return JSONResponse(status_code=403, content=error.model_dump(mode="json"))
    except AccountNotFoundError:
        error = ApiError(code="INVALID_REQUEST", message="A transfer account was not found.")
        return JSONResponse(status_code=404, content=error.model_dump(mode="json"))
    except IdempotencyKeyConflictError:
        error = ApiError(
            code="IDEMPOTENCY_KEY_REUSED",
            message="This idempotency key was already used for a different request.",
        )
        return JSONResponse(status_code=409, content=error.model_dump(mode="json"))

    transaction = outcome.transaction
    response = TransferResponse(
        transaction_id=transaction.transaction_id,
        from_account=mask_account_number(transaction.from_account),
        to_account=mask_account_number(transaction.to_account),
        amount=f"{transaction.amount:.2f}",
        status=transaction.status.value,
        created_at=transaction.created_at,
        error_code=(
            None if transaction.error_code is None else transaction.error_code.value
        ),
        message=(
            "Transfer completed."
            if transaction.status.value == "completed"
            else REJECTION_MESSAGES[transaction.error_code.value]
        ),
    )
    return JSONResponse(
        status_code=200 if outcome.replayed else 201,
        content=response.model_dump(mode="json"),
    )
