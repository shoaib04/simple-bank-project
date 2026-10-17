from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class TransactionStatus(str, Enum):
    COMPLETED = "completed"
    REJECTED = "rejected"


class TransferErrorCode(str, Enum):
    INVALID_AMOUNT = "INVALID_AMOUNT"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    DAILY_LIMIT_EXCEEDED = "DAILY_LIMIT_EXCEEDED"
    SAME_AMOUNT = "SAME_AMOUNT"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String, primary_key=True)
    accounts: Mapped[list[Account]] = relationship(back_populates="customer")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="customer")


class Account(Base):
    __tablename__ = "accounts"

    account_number: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[AccountStatus] = mapped_column(
        SqlEnum(
            AccountStatus,
            name="account_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    customer: Mapped[Customer] = relationship(back_populates="accounts")
    outgoing_transactions: Mapped[list[Transaction]] = relationship(
        back_populates="source_account", foreign_keys="Transaction.from_account"
    )
    incoming_transactions: Mapped[list[Transaction]] = relationship(
        back_populates="recipient_account", foreign_keys="Transaction.to_account"
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint(
            "customer_id", "idempotency_key", name="uq_transactions_customer_idempotency"
        ),
        CheckConstraint(
            "status != 'completed' OR (amount > 0 AND from_account != to_account)",
            name="ck_completed_transfer_valid",
        ),
        CheckConstraint(
            "(status = 'completed' AND error_code IS NULL) OR "
            "(status = 'rejected' AND error_code IS NOT NULL)",
            name="ck_transaction_error_code_by_status",
        ),
        CheckConstraint(
            "(status = 'completed' AND from_balance_after IS NOT NULL "
            "AND to_balance_after IS NOT NULL) OR "
            "(status = 'rejected' AND from_balance_after IS NULL "
            "AND to_balance_after IS NULL)",
            name="ck_transaction_balance_snapshots_by_status",
        ),
        Index(
            "ix_transactions_from_account_created_id",
            "from_account",
            "created_at",
            "transaction_id",
        ),
        Index(
            "ix_transactions_to_account_created_id",
            "to_account",
            "created_at",
            "transaction_id",
        ),
    )

    transaction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    from_account: Mapped[str] = mapped_column(
        ForeignKey("accounts.account_number"), nullable=False
    )
    to_account: Mapped[str] = mapped_column(
        ForeignKey("accounts.account_number"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    from_balance_after: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    to_balance_after: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    status: Mapped[TransactionStatus] = mapped_column(
        SqlEnum(
            TransactionStatus,
            name="transaction_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    error_code: Mapped[TransferErrorCode | None] = mapped_column(
        SqlEnum(
            TransferErrorCode,
            name="transfer_error_code",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=True,
    )
    customer: Mapped[Customer] = relationship(back_populates="transactions")
    source_account: Mapped[Account] = relationship(
        back_populates="outgoing_transactions", foreign_keys=[from_account]
    )
    recipient_account: Mapped[Account] = relationship(
        back_populates="incoming_transactions", foreign_keys=[to_account]
    )
