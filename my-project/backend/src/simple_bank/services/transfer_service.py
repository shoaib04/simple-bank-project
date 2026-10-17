from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from simple_bank.db.models import (
    Account,
    Customer,
    Transaction,
    TransactionStatus,
    TransferErrorCode,
)
from simple_bank.logging import log_transfer_accounts
from simple_bank.schemas.transfers import TransferRequest
from simple_bank.services.transfer_rules import TransferFacts, TransferRulesService


class AccountNotFoundError(Exception):
    pass


class SourceAccountForbiddenError(Exception):
    pass


class IdempotencyKeyConflictError(Exception):
    pass


@dataclass(frozen=True)
class TransferOutcome:
    transaction: Transaction
    message: str
    replayed: bool = False


class TransferService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_transfer(
        self, customer_id: str, request: TransferRequest
    ) -> TransferOutcome:
        evaluated_at = datetime.now(UTC)
        day_start = evaluated_at.replace(hour=0, minute=0, second=0, microsecond=0)
        next_day = day_start + timedelta(days=1)
        amount = TransferRulesService.normalize_amount(request.amount)

        async with self.session.begin():
            customer = await self.session.scalar(
                select(Customer)
                .where(Customer.customer_id == customer_id)
                .with_for_update()
            )
            if customer is None:
                raise SourceAccountForbiddenError("Authenticated customer is unavailable")

            existing_transaction = await self.session.scalar(
                select(Transaction).where(
                    Transaction.customer_id == customer_id,
                    Transaction.idempotency_key == request.idempotency_key,
                )
            )
            if existing_transaction is not None:
                same_request = (
                    existing_transaction.from_account == request.from_account
                    and existing_transaction.to_account == request.to_account
                    and existing_transaction.amount == amount
                )
                if not same_request:
                    raise IdempotencyKeyConflictError(
                        "Idempotency key was already used with a different request"
                    )
                log_transfer_accounts(
                    existing_transaction.from_account,
                    existing_transaction.to_account,
                    existing_transaction.status.value,
                )
                return TransferOutcome(
                    transaction=existing_transaction,
                    message=self._message_for(existing_transaction),
                    replayed=True,
                )

            account_numbers = sorted({request.from_account, request.to_account})
            locked_accounts = await self.session.scalars(
                select(Account)
                .where(Account.account_number.in_(account_numbers))
                .order_by(Account.account_number)
                .with_for_update()
            )
            accounts = {account.account_number: account for account in locked_accounts}
            source_account = accounts.get(request.from_account)
            destination_account = accounts.get(request.to_account)
            if source_account is None or destination_account is None:
                raise AccountNotFoundError("A transfer account was not found")
            if source_account.customer_id != customer_id:
                raise SourceAccountForbiddenError("Source account does not belong to customer")

            customer_total = await self._completed_outgoing_total(
                Transaction.customer_id == customer_id,
                day_start,
                next_day,
            )
            source_total = await self._completed_outgoing_total(
                Transaction.from_account == source_account.account_number,
                day_start,
                next_day,
            )
            decision = TransferRulesService.evaluate(
                TransferFacts(
                    source_account_number=source_account.account_number,
                    destination_account_number=destination_account.account_number,
                    amount=amount,
                    source_balance=source_account.balance,
                    customer_outgoing_today=customer_total,
                    source_outgoing_today=source_total,
                    source_opened_at=source_account.opened_at,
                    evaluated_at=evaluated_at,
                    source_active=source_account.status.value == "active",
                    destination_active=destination_account.status.value == "active",
                )
            )

            completed = decision.status == "completed"
            transaction = Transaction(
                from_account=source_account.account_number,
                to_account=destination_account.account_number,
                amount=amount,
                status=(
                    TransactionStatus.COMPLETED if completed else TransactionStatus.REJECTED
                ),
                created_at=evaluated_at,
                customer_id=customer_id,
                idempotency_key=request.idempotency_key,
                error_code=(
                    None
                    if decision.error_code is None
                    else TransferErrorCode(decision.error_code)
                ),
            )
            if completed:
                source_account.balance -= amount
                destination_account.balance += amount
                transaction.from_balance_after = source_account.balance
                transaction.to_balance_after = destination_account.balance
            self.session.add(transaction)
            await self.session.flush()
            log_transfer_accounts(
                source_account.account_number,
                destination_account.account_number,
                transaction.status.value,
            )

            return TransferOutcome(
                transaction=transaction,
                message=self._message_for(transaction),
            )

    @staticmethod
    def _message_for(transaction: Transaction) -> str:
        if transaction.status == TransactionStatus.COMPLETED:
            return "Transfer completed."
        return f"Transfer rejected: {transaction.error_code.value}."

    async def _completed_outgoing_total(
        self, scope, day_start: datetime, next_day: datetime
    ) -> Decimal:
        total = await self.session.scalar(
            select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
                scope,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= day_start,
                Transaction.created_at < next_day,
            )
        )
        return total or Decimal("0.00")
