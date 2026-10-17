import sqlalchemy as sa

from alembic import op

revision = "0002_transfer_balance_snapshots"
down_revision = "0001_transfer_schema"
branch_labels = None
depends_on = None


BACKFILL_SNAPSHOTS_SQL = sa.text(
    """
    WITH account_events AS (
        SELECT
            transaction_id,
            from_account AS account_number,
            created_at,
            -amount AS delta,
            'from'::text AS side
        FROM transactions
        WHERE status = 'completed'
        UNION ALL
        SELECT
            transaction_id,
            to_account AS account_number,
            created_at,
            amount AS delta,
            'to'::text AS side
        FROM transactions
        WHERE status = 'completed'
    ),
    event_balances AS (
        SELECT
            account_event.transaction_id,
            account_event.side,
            account.balance - COALESCE(
                SUM(account_event.delta) OVER (
                    PARTITION BY account_event.account_number
                    ORDER BY account_event.created_at DESC, account_event.transaction_id DESC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ),
                0.00
            ) AS balance_after
        FROM account_events AS account_event
        JOIN accounts AS account
            ON account.account_number = account_event.account_number
    ),
    snapshots AS (
        SELECT
            transaction_id,
            MAX(balance_after) FILTER (WHERE side = 'from') AS from_balance_after,
            MAX(balance_after) FILTER (WHERE side = 'to') AS to_balance_after
        FROM event_balances
        GROUP BY transaction_id
    )
    UPDATE transactions AS txn
    SET
        from_balance_after = snapshots.from_balance_after,
        to_balance_after = snapshots.to_balance_after
    FROM snapshots
    WHERE txn.transaction_id = snapshots.transaction_id
    """
)


VERIFY_LATEST_SNAPSHOTS_SQL = sa.text(
    """
    DO $$
    BEGIN
        IF EXISTS (
            WITH account_side_balances AS (
                SELECT
                    from_account AS account_number,
                    created_at,
                    transaction_id,
                    from_balance_after AS balance_after
                FROM transactions
                WHERE status = 'completed'
                UNION ALL
                SELECT
                    to_account AS account_number,
                    created_at,
                    transaction_id,
                    to_balance_after AS balance_after
                FROM transactions
                WHERE status = 'completed'
            ),
            latest_balances AS (
                SELECT DISTINCT ON (account_number)
                    account_number,
                    balance_after
                FROM account_side_balances
                ORDER BY account_number, created_at DESC, transaction_id DESC
            )
            SELECT 1
            FROM accounts AS account
            JOIN latest_balances AS latest USING (account_number)
            WHERE account.balance IS DISTINCT FROM latest.balance_after
        ) THEN
            RAISE EXCEPTION
                'Mini Statement snapshot backfill does not reconcile with current account balances';
        END IF;
    END
    $$
    """
)


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("from_balance_after", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("to_balance_after", sa.Numeric(18, 2), nullable=True),
    )

    op.create_index(
        "ix_transactions_from_account_created_id",
        "transactions",
        ["from_account", "created_at", "transaction_id"],
    )
    op.create_index(
        "ix_transactions_to_account_created_id",
        "transactions",
        ["to_account", "created_at", "transaction_id"],
    )

    op.execute(BACKFILL_SNAPSHOTS_SQL)
    op.execute(VERIFY_LATEST_SNAPSHOTS_SQL)
    op.create_check_constraint(
        "ck_transaction_balance_snapshots_by_status",
        "transactions",
        "(status = 'completed' AND from_balance_after IS NOT NULL "
        "AND to_balance_after IS NOT NULL) OR "
        "(status = 'rejected' AND from_balance_after IS NULL "
        "AND to_balance_after IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_transaction_balance_snapshots_by_status",
        "transactions",
        type_="check",
    )
    op.drop_index("ix_transactions_to_account_created_id", table_name="transactions")
    op.drop_index("ix_transactions_from_account_created_id", table_name="transactions")
    op.drop_column("transactions", "to_balance_after")
    op.drop_column("transactions", "from_balance_after")
