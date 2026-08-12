from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from common.domain.exceptions import DomainError


def money(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise DomainError("Enter a valid amount.", "invalid_amount")
    if amount <= 0:
        raise DomainError("Amount must be greater than zero.", "invalid_amount")
    return amount
