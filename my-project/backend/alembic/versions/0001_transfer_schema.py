import sqlalchemy as sa

from alembic import op

revision = "0001_transfer_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("customer_id"),
    )
    op.create_table(
        "accounts",
        sa.Column("account_number", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "inactive",
                name="account_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"]),
        sa.PrimaryKeyConstraint("account_number"),
    )
    op.create_index("ix_accounts_customer_id", "accounts", ["customer_id"])
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("from_account", sa.String(), nullable=False),
        sa.Column("to_account", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "completed",
                "rejected",
                name="transaction_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "error_code",
            sa.Enum(
                "INVALID_AMOUNT",
                "INSUFFICIENT_BALANCE",
                "DAILY_LIMIT_EXCEEDED",
                "SAME_AMOUNT",
                "ACCOUNT_INACTIVE",
                name="transfer_error_code",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status != 'completed' OR (amount > 0 AND from_account != to_account)",
            name="ck_completed_transfer_valid",
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND error_code IS NULL) OR "
            "(status = 'rejected' AND error_code IS NOT NULL)",
            name="ck_transaction_error_code_by_status",
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"]),
        sa.ForeignKeyConstraint(["from_account"], ["accounts.account_number"]),
        sa.ForeignKeyConstraint(["to_account"], ["accounts.account_number"]),
        sa.PrimaryKeyConstraint("transaction_id"),
        sa.UniqueConstraint(
            "customer_id", "idempotency_key", name="uq_transactions_customer_idempotency"
        ),
    )
    op.create_index("ix_transactions_customer_id", "transactions", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_customer_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_accounts_customer_id", table_name="accounts")
    op.drop_table("accounts")
    op.drop_table("customers")
