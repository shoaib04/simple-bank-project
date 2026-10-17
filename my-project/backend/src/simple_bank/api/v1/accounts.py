from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from simple_bank.api.dependencies import get_current_customer_id, get_mini_statement_service
from simple_bank.schemas.mini_statement import MiniStatementResponse
from simple_bank.services.mini_statement_service import MiniStatementService

router = APIRouter()


@router.get(
    "/accounts/{account_number}/mini-statement",
    response_model=MiniStatementResponse,
    status_code=status.HTTP_200_OK,
)
async def get_mini_statement(
    account_number: str,
    customer_id: Annotated[str, Depends(get_current_customer_id)],
    service: Annotated[MiniStatementService, Depends(get_mini_statement_service)],
) -> MiniStatementResponse:
    statement = await service.get_statement(
        customer_id=customer_id,
        account_number=account_number,
    )
    if statement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account statement was not found.",
        )
    return statement
