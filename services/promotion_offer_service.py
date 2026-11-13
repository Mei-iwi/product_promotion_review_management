"""Customer-visible vouchers and live cart eligibility; never reserve usage here."""
import re
from repositories import promotion_repository as repo, shopping_repository
from repositories.security_repository import utcnow
from services import cart_service
from services.promotion_pricing import calculate
from services.shopping_common import ShoppingError, money, utc
from services.helpers import ValidationError


def describe(promos):
    names, groups = repo.target_labels(promos)
    rows = []
    now = utcnow()
    for promo in promos:
        conditions, targets = promo.get('conditions', {}), promo.get('targets', {})
        labels = [names.get(c, c) for c in targets.get('productCodes', [])]
        labels += [groups.get(c, c) for c in targets.get('categories', [])]
        upcoming = utc(promo['startDate']) > utc(now)
        exhausted = promo.get('usageLimit', 0) > 0 and promo.get('commerceUsed', 0) >= promo['usageLimit']
        rows.append({'promoCode': promo['promoCode'], 'name': promo['name'],
                     'percentage': promo['value'] if promo['promoType'] == 'percentage' else None,
                     'amount': money(promo['value']) if promo['promoType'] == 'fixed' else None,
                     'minimum': money(conditions.get('minOrderValue', 0)),
                     'maximum': money(conditions.get('maxDiscount', 0)),
                     'startDate': promo['startDate'], 'endDate': promo['endDate'],
                     'scope': ', '.join(labels) if labels else 'Tất cả sản phẩm',
                     'available': not upcoming and not exhausted,
                     'state': 'Chưa đến thời gian áp dụng' if upcoming else ('Đã hết lượt' if exhausted else 'Đang áp dụng')})
    return rows


def for_cart(principal):
    cart_service.require_customer(principal, 'cart.read_own')
    cart = shopping_repository.cart(principal)
    if not cart['items']:
        return []
    try:
        priced = cart_service.price_cart({**cart, 'promoCode': ''})
    except ShoppingError:
        return []
    promos, discounts = [], {}
    for promo in repo.public_offers():
        try:
            discount = calculate(promo, priced['lines'], priced['subtotal'])
        except ShoppingError:
            continue
        if discount > 0:
            promos.append(promo)
            discounts[promo['promoCode']] = discount
    rows = describe(promos)
    for row in rows:
        row['discount'] = discounts[row['promoCode']]
    return sorted(rows, key=lambda row: (-row['discount'], row['promoCode']))


def listing(filters):
    if set(filters) - {'page'} or (hasattr(filters, 'getlist') and len(filters.getlist('page')) > 1):
        raise ValidationError('Bộ lọc mã giảm giá không hợp lệ')
    page = filters.get('page', '1')
    if not isinstance(page, str) or not re.fullmatch(r'[0-9]{1,6}', page) or not 1 <= int(page) <= 100000:
        raise ValidationError('Trang mã giảm giá không hợp lệ')
    page = int(page)
    promos, total = repo.public_offers(page=page)
    return {'rows': describe(promos), 'total': total, 'page': page, 'pages': max(1, (total + 11) // 12)}
