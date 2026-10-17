from fastapi import APIRouter

from simple_bank.api.v1.accounts import router as accounts_router
from simple_bank.api.v1.transfers import router as transfers_router

router = APIRouter()
router.include_router(accounts_router)
router.include_router(transfers_router)
