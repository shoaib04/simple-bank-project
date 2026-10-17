import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

CENT = Decimal("0.01")
AMOUNT_PATTERN = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")
TransferErrorCode = Literal[
    "INSUFFICIENT_BALANCE",
    "DAILY_LIMIT_EXCEEDED",
    "SAME_AMOUNT",
    "ACCOUNT_INACTIVE",
    "INVALID_AMOUNT",
]


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_account: StrictStr = Field(min_length=1)
    to_account: StrictStr = Field(min_length=1)
    amount: Decimal
    idempotency_key: StrictStr = Field(min_length=1, max_length=255)

    @field_validator("amount", mode="before")
    @classmethod
    def parse_decimal_string(cls, value: object) -> Decimal:
        if not isinstance(value, str) or not AMOUNT_PATTERN.fullmatch(value):
            raise ValueError("amount must be a decimal string")
        try:
            amount = Decimal(value)
            if not amount.is_finite():
                raise ValueError("amount must be a finite decimal")
            return amount.quantize(CENT, rounding=ROUND_HALF_UP)
        except InvalidOperation as error:
            raise ValueError("amount must be a valid decimal string") from error


class TransferResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: UUID
    from_account: StrictStr = Field(pattern=r"^XXXX[0-9]{4}$")
    to_account: StrictStr = Field(pattern=r"^XXXX[0-9]{4}$")
    amount: StrictStr = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    status: Literal["completed", "rejected"]
    created_at: datetime
    error_code: TransferErrorCode | None
    message: StrictStr


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["IDEMPOTENCY_KEY_REUSED", "INVALID_REQUEST", "FORBIDDEN"]
    message: StrictStr
