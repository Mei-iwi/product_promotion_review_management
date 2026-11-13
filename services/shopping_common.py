from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from services.helpers import ValidationError

VIETNAM = timezone(timedelta(hours=7))


class ShoppingError(ValidationError):
    def __init__(self, message, code='invalid', status=400, field=None):
        super().__init__(message)
        self.code, self.status, self.field = code, status, field


def utc(value):
    """MongoDB BSON dates without tzinfo represent UTC, never host local time."""
    if not isinstance(value, datetime):
        raise ShoppingError('Ngày khuyến mãi không hợp lệ', 'invalid_promotion')
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def money(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal('1000000000000'):
            raise InvalidOperation()
        return int(amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (ValueError, TypeError, InvalidOperation):
        raise ShoppingError('Số tiền không hợp lệ', 'invalid_price')


def quantity(value):
    import re
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not re.fullmatch(r'[0-9]{1,2}', str(value)) or not 1 <= int(value) <= 99:
        raise ShoppingError('Số lượng phải là số nguyên từ 1 đến 99', 'invalid_quantity', field='quantity')
    return int(value)
