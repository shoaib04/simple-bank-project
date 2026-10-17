from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

MoneyString = Annotated[StrictStr, Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")]
PositiveMoneyString = Annotated[StrictStr, Field(pattern=r"^[0-9]+\.[0-9]{2}$")]


class MiniStatementEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime
    description: StrictStr
    debit: PositiveMoneyString
    credit: PositiveMoneyString
    amount: PositiveMoneyString
    balance_after: MoneyString

    @field_validator("date")
    @classmethod
    def normalize_date_to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("statement dates must include a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_amount_direction(self) -> MiniStatementEntry:
        amount = Decimal(self.amount)
        debit = Decimal(self.debit)
        credit = Decimal(self.credit)
        if amount <= 0:
            raise ValueError("statement amount must be positive")
        if not (
            (debit == amount and credit == 0)
            or (credit == amount and debit == 0)
        ):
            raise ValueError("exactly one matching debit or credit is required")
        return self


class MiniStatementResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_number: StrictStr = Field(pattern=r"^XXXX[0-9]{4}$")
    transactions: list[MiniStatementEntry] = Field(max_length=10)
