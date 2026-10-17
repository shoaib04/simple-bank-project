from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from simple_bank.db.session import get_db_session
from simple_bank.services.mini_statement_service import MiniStatementService
from simple_bank.services.transfer_service import TransferService


def get_current_customer_id(request: Request) -> str:
    customer_id = getattr(request.state, "customer_id", None)
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="An authenticated customer context is required.",
        )
    return str(customer_id)


def get_transfer_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TransferService:
    return TransferService(session)


def get_mini_statement_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MiniStatementService:
    return MiniStatementService(session)
