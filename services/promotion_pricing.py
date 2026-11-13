"""One promotion calculation for both cart preview and transactional checkout."""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from repositories.security_repository import utcnow
from services.shopping_common import ShoppingError, utc, money


def calculate(promo, lines, subtotal, now=None):
    if not promo:
        raise ShoppingError('Mã giảm giá không tồn tại', 'promo_not_found', field='promoCode')
    if promo.get('status') != 'active':
        message = 'Mã giảm giá đã hết hạn' if promo.get('status') == 'expired' else 'Mã giảm giá không hoạt động'
        raise ShoppingError(message, 'promo_expired' if promo.get('status') == 'expired' else 'promo_inactive', field='promoCode')
    now = utc(now or utcnow())
    if now < utc(promo.get('startDate')):
        raise ShoppingError('Mã giảm giá chưa đến thời gian áp dụng', 'promo_not_started', field='promoCode')
    if now > utc(promo.get('endDate')):
        raise ShoppingError('Mã giảm giá đã hết hạn', 'promo_expired', field='promoCode')
    limit, used = promo.get('usageLimit', 0), promo.get('commerceUsed', 0)
    if limit > 0 and used >= limit:
        raise ShoppingError('Mã giảm giá đã hết lượt', 'promo_exhausted', field='promoCode')
    conditions, targets = promo.get('conditions', {}), promo.get('targets', {})
    if subtotal < money(conditions.get('minOrderValue', 0)):
        raise ShoppingError('Giỏ chưa đạt giá trị đơn tối thiểu của mã', 'promo_minimum', field='promoCode')
    codes, categories = targets.get('productCodes', []), targets.get('categories', [])
    eligible = sum(line['lineTotal'] for line in lines if
                   (not codes and not categories) or line['productCode'] in codes or line['categoryCode'] in categories)
    if eligible <= 0:
        raise ShoppingError('Giỏ chưa có sản phẩm đủ điều kiện áp mã', 'promo_no_eligible', field='promoCode')
    try:
        value = Decimal(str(promo['value']))
        if not value.is_finite() or value < 0:
            raise InvalidOperation()
        if promo['promoType'] == 'percentage' and value <= 100:
            discount = int((Decimal(eligible) * value / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        elif promo['promoType'] == 'fixed':
            discount = money(value)
        else:
            raise InvalidOperation()
    except (InvalidOperation, KeyError, TypeError):
        raise ShoppingError('Cấu hình giảm giá không hợp lệ', 'invalid_promotion')
    cap = money(conditions.get('maxDiscount', 0))
    return min(discount, eligible, cap if cap > 0 else eligible)
