from datetime import UTC
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from simple_bank.db.models import Account, Transaction, TransactionStatus
from simple_bank.schemas.mini_statement import MiniStatementEntry, MiniStatementResponse
from simple_bank.security.account_masking import mask_account_number


class MiniStatementService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_statement(
        self, customer_id: str, account_number: str
    ) -> MiniStatementResponse | None:
        account = await self.session.scalar(
            select(Account).where(
                Account.account_number == account_number,
                Account.customer_id == customer_id,
            )
        )
        if account is None:
            return None

        rows = await self.session.scalars(
            select(Transaction)
            .where(
                Transaction.status == TransactionStatus.COMPLETED,
                or_(
                    Transaction.from_account == account_number,
                    Transaction.to_account == account_number,
                ),
            )
            .order_by(Transaction.created_at.desc(), Transaction.transaction_id.desc())
            .limit(10)
        )
        entries = [self._to_entry(transaction, account_number) for transaction in rows]
        return MiniStatementResponse(
            account_number=mask_account_number(account_number),
            transactions=entries,
        )

    @staticmethod
    def _to_entry(transaction: Transaction, account_number: str) -> MiniStatementEntry:
        amount = transaction.amount
        if transaction.from_account == account_number:
            debit = amount
            credit = Decimal("0.00")
            balance_after = transaction.from_balance_after
            counterparty = mask_account_number(transaction.to_account)
            description = f"Transfer to {counterparty}"
        else:
            debit = Decimal("0.00")
            credit = amount
            balance_after = transaction.to_balance_after
            counterparty = mask_account_number(transaction.from_account)
            description = f"Transfer from {counterparty}"

        if balance_after is None:
            raise RuntimeError("Completed transaction is missing its balance snapshot")

        created_at = transaction.created_at
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            created_at = created_at.replace(tzinfo=UTC)
        else:
            created_at = created_at.astimezone(UTC)

        return MiniStatementEntry(
            date=created_at,
            description=description,
            debit=f"{debit:.2f}",
            credit=f"{credit:.2f}",
            amount=f"{amount:.2f}",
            balance_after=f"{balance_after:.2f}",
        )
