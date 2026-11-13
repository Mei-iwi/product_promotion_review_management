import hashlib
import json
import re
from repositories import shopping_repository as repo
from services.access_policy import has_permission
from services.shopping_common import ShoppingError, money, quantity
from services.promotion_pricing import calculate

MAX_LINES = 50


def require_customer(principal, permission='cart.manage_own'):
    if not has_permission(principal, permission):
        from werkzeug.exceptions import Forbidden
        raise Forbidden()


def code(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
        raise ShoppingError('Mã sản phẩm hoặc mã giảm giá không hợp lệ', field='productCode')
    return value


def price_cart(cart, session=None):
    docs = repo.products([row['productCode'] for row in cart['items']], session)
    lines, stock_snapshot = [], []
    for row in cart['items']:
        product = docs.get(row['productCode'])
        if not product or product.get('status') != 'active':
            raise ShoppingError('Sản phẩm trong giỏ không còn hoạt động; hãy xóa dòng này', 'unavailable_product', 409)
        amount = quantity(row['quantity'])
        if product.get('stock', 0) < amount:
            raise ShoppingError('Số lượng trong giỏ vượt quá lượng hàng còn bán; hãy giảm số lượng', 'insufficient_stock', 409)
        unit = money(product['price'])
        lines.append({'productCode': product['productCode'], 'productName': product['name'], 'quantity': amount,
                      'unitPrice': unit, 'lineTotal': unit * amount,
                      'categoryCode': product.get('category', {}).get('categoryCode', '')})
        stock_snapshot.append([product['productCode'], product.get('stock'), str(product['price']), product['status']])
    subtotal = sum(line['lineTotal'] for line in lines)
    promo = repo.promotion(cart.get('promoCode'), session)
    discount = calculate(promo, lines, subtotal) if cart.get('promoCode') else 0
    snapshot = {'lines': lines, 'stock': stock_snapshot, 'promotion': {
        k: v for k, v in (promo or {}).items() if k != '_id'}, 'cartVersion': cart['version']}
    fingerprint = hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str, ensure_ascii=True).encode()).hexdigest()
    return {'lines': lines, 'subtotal': subtotal, 'discount': discount, 'shippingFee': 0,
            'total': subtotal - discount, 'promoCode': cart.get('promoCode', ''), 'fingerprint': fingerprint}


def view(principal):
    require_customer(principal, 'cart.read_own')
    cart = repo.cart(principal)
    try:
        return {**price_cart(cart), 'error': None, 'items': cart['items']}
    except ShoppingError as error:
        # Keep persisted rows visible/removable even when a product/promotion was
        # disabled or stock changed. Never expose exact stock in the view model.
        docs = repo.products([r['productCode'] for r in cart['items']])
        lines = [{'productCode': r['productCode'], 'productName': docs.get(r['productCode'], {}).get('name', 'Sản phẩm không khả dụng'),
                  'quantity': r['quantity'], 'unitPrice': money(docs.get(r['productCode'], {}).get('price', 0)),
                  'lineTotal': money(docs.get(r['productCode'], {}).get('price', 0)) * r['quantity']} for r in cart['items']]
        return {'lines': lines, 'items': cart['items'], 'subtotal': sum(r['lineTotal'] for r in lines),
                'discount': 0, 'shippingFee': 0, 'total': None, 'promoCode': cart.get('promoCode', ''), 'error': str(error)}


def change(principal, action, product_code=None, amount=None, promo_code=None):
    require_customer(principal)
    if action not in {'add', 'set', 'remove', 'apply', 'clear_promo'}:
        raise ShoppingError('Thao tác giỏ hàng không hợp lệ')
    if action in {'add', 'set', 'remove'}:
        product_code = code(product_code)
    if action in {'add', 'set'}:
        amount = quantity(amount)
    if action == 'apply':
        promo_code = code(promo_code)
    for _ in range(8):
        old = repo.cart(principal)
        items = {row['productCode']: row['quantity'] for row in old['items']}
        promotion = old.get('promoCode', '')
        if action in {'add', 'set'}:
            desired = quantity((items.get(product_code, 0) + amount) if action == 'add' else amount)
            product = repo.products([product_code]).get(product_code)
            if not product or product.get('status') != 'active' or product.get('stock', 0) < desired:
                raise ShoppingError('Sản phẩm không khả dụng hoặc số lượng vượt lượng hàng còn bán', 'insufficient_stock', field='quantity')
            items[product_code] = desired
        if action == 'remove':
            items.pop(product_code, None)
        if len(items) > MAX_LINES:
            raise ShoppingError('Giỏ hàng tối đa 50 sản phẩm khác nhau', 'cart_full')
        rows = [{'productCode': k, 'quantity': v} for k, v in sorted(items.items())]
        if action == 'clear_promo':
            promotion = ''
        if action == 'apply':
            candidate = {**old, 'items': rows, 'promoCode': promo_code}
            price_cart(candidate)  # Preview only; never increment usage.
            promotion = promo_code
        if repo.save_cart(principal, old, rows, promotion):
            return view(principal)
    raise ShoppingError('Giỏ vừa thay đổi ở cửa sổ khác; vui lòng thử lại', 'cart_conflict', 409)
