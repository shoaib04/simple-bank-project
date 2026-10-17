import logging

from simple_bank.security.account_masking import mask_account_number

transfer_logger = logging.getLogger("simple_bank.transfer")


def log_transfer_accounts(
    source_account_number: str,
    destination_account_number: str,
    status: str | None = None,
) -> None:
    source_reference = mask_account_number(source_account_number)
    destination_reference = mask_account_number(destination_account_number)
    status_detail = f" {status}" if status else ""
    transfer_logger.info(
        "Transfer%s accounts %s -> %s",
        status_detail,
        source_reference,
        destination_reference,
    )
