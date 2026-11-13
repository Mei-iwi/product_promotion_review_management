import hashlib
import json
import re
import secrets
from datetime import timedelta
from flask import current_app
from pymongo.errors import DuplicateKeyError
from werkzeug.exceptions import NotFound
from db.mongo import get_db
from repositories import shopping_repository as repo
from repositories.security_repository import utcnow
from services import cart_service
from services.shopping_common import ShoppingError, utc


def availability(require_enabled=True):
    if require_enabled and not current_app.config.get('CHECKOUT_ENABLED'):
        return 'Đặt hàng chưa được bật trên hệ thống.'
    if not repo.transaction_supported():
        return 'Đặt hàng cần MongoDB replica set; danh mục và tra cứu vẫn dùng được.'
    if not get_db().shopping_state.find_one({'_id': repo.STATE_KEY, 'ready': True}):
        return 'Cần đối soát lượt khuyến mãi trước khi bật đặt hàng.'
    return None


def require_ready(require_enabled=True):
    message = availability(require_enabled)
    if message:
        raise ShoppingError(message, 'checkout_unavailable', 503)


def shipping(data):
    if not isinstance(data, dict) or set(data) - {'fullName', 'address', 'phone'}:
        raise ShoppingError('Thông tin nhận hàng chứa trường không được phép')
    result = {}
    for field, label, minimum, maximum in [('fullName', 'Họ tên', 2, 100), ('address', 'Địa chỉ', 8, 500), ('phone', 'Số điện thoại', 9, 25)]:
        value = data.get(field)
        if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
            raise ShoppingError(label + ' không hợp lệ', field=field)
        result[field] = value.strip()
    phone = re.sub(r'[ ()-]', '', result['phone'])
    if not re.fullmatch(r'\+?[0-9]{9,15}', phone):
        raise ShoppingError('Số điện thoại phải có từ 9 đến 15 chữ số', field='phone')
    result['phone'] = phone
    return result


def quote_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,80}', value):
        raise NotFound()
    return value


def create_quote(principal):
    cart_service.require_customer(principal, 'orders.create_own')
    require_ready()
    cart = repo.cart(principal)
    if not cart['items']:
        raise ShoppingError('Giỏ hàng đang trống', 'empty_cart')
    priced = cart_service.price_cart(cart)
    now = utcnow()
    quote = {**priced, '_id': secrets.token_urlsafe(32), 'userId': principal['_id'],
             'customerCode': principal['customerCode'], 'cartVersion': cart['version'],
             'createdAt': now, 'expiresAt': now + timedelta(minutes=15)}
    get_db().checkout_quotes.insert_one(quote)
    return quote


def get_quote(principal, key):
    cart_service.require_customer(principal, 'orders.create_own')
    row = repo.quote(principal, quote_key(key))
    if not row:
        raise NotFound()
    return row


def change_promotion(principal, key, promo_code):
    if not isinstance(promo_code, str):
        raise ShoppingError('Mã giảm giá không hợp lệ')
    previous = get_quote(principal, key)
    require_ready()
    cart = repo.cart(principal)
    if utc(previous['expiresAt']) <= utc(utcnow()) or cart['version'] != previous['cartVersion']:
        raise ShoppingError('Giỏ hàng hoặc xác nhận đã thay đổi; hãy quay lại giỏ và xác nhận lại', 'cart_conflict', 409)
    cart_service.change(principal, 'apply' if promo_code else 'clear_promo', promo_code=promo_code)
    return create_quote(principal)


def request_hash(key, recipient):
    return hashlib.sha256(json.dumps({'quote': key, 'recipient': recipient}, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def replay(order, fingerprint):
    if order.get('requestHash') != fingerprint:
        raise ShoppingError('Lần đặt hàng này đã dùng với nội dung khác', 'idempotency_conflict', 409)
    return order


def validate_principal(principal, session):
    db = get_db()
    user = db.users.find_one({'_id': principal['_id'], 'role': 'CUSTOMER', 'status': 'active',
                              'customerCode': principal['customerCode'], 'authVersion': principal['authVersion']}, session=session)
    customer = db.customers.find_one({'customerCode': principal['customerCode'], 'status': 'active'}, session=session)
    if not user or not customer:
        from werkzeug.exceptions import Forbidden
        raise Forbidden()


def place_order(principal, key, data):
    cart_service.require_customer(principal, 'orders.create_own')
    key, recipient = quote_key(key), shipping(data)
    fingerprint = request_hash(key, recipient)
    existing = repo.existing_order(principal, key)
    if existing:
        return replay(existing, fingerprint)
    require_ready()
    order_code = 'DONHANG' + secrets.token_hex(12).upper()

    def commit(session):
        db = get_db()
        existing = repo.existing_order(principal, key, session)
        if existing:
            return replay(existing, fingerprint)
        if not repo.fence(session):
            raise ShoppingError('Đặt hàng chưa được đối soát', 'checkout_unavailable', 503)
        validate_principal(principal, session)
        quote = repo.quote(principal, key, session)
        if not quote:
            raise NotFound()
        if utc(quote['expiresAt']) <= utc(utcnow()):
            raise ShoppingError('Xác nhận thanh toán đã hết hạn; hãy xem lại giỏ', 'quote_expired', 409)
        cart = repo.cart(principal, session)
        priced = cart_service.price_cart(cart, session)
        if not cart['items'] or cart['version'] != quote['cartVersion'] or priced['fingerprint'] != quote['fingerprint']:
            raise ShoppingError('Giá, tồn kho hoặc ưu đãi vừa thay đổi; hãy xem lại giỏ và xác nhận lại tổng tiền', 'quote_changed', 409)
        for line in priced['lines']:
            changed = db.products.update_one({'productCode': line['productCode'], 'status': 'active', 'stock': {'$gte': line['quantity']}},
                                             {'$inc': {'stock': -line['quantity']}}, session=session)
            if changed.modified_count != 1:
                raise ShoppingError('Sản phẩm vừa hết hàng; hãy xem lại giỏ', 'insufficient_stock', 409)
        promo_code = cart.get('promoCode', '')
        if promo_code:
            promo = repo.promotion(promo_code, session)
            query = {'_id': promo['_id'], 'status': 'active'}
            if promo.get('usageLimit', 0) > 0:
                query['$expr'] = {'$lt': [{'$ifNull': ['$commerceUsed', 0]}, promo['usageLimit']]}
            if db.promotions.update_one(query, {'$inc': {'commerceUsed': 1}}, session=session).modified_count != 1:
                raise ShoppingError('Mã giảm giá vừa hết lượt', 'promo_exhausted', 409)
        now = utcnow()
        order = {'orderCode': order_code, 'customerCode': principal['customerCode'], 'orderDate': now,
                 'items': [{k: line[k] for k in ['productCode', 'productName', 'quantity', 'unitPrice']} for line in priced['lines']],
                 'appliedPromotion': {'promoCode': promo_code, 'discountAmount': priced['discount']} if promo_code else None,
                 'subtotal': priced['subtotal'], 'shippingFee': 0, 'totalAmount': priced['total'],
                 'status': 'pending', 'paymentMethod': 'COD', 'recipient': recipient,
                 'statusHistory': [{'status': 'pending', 'at': now, 'actorUserId': principal['_id'], 'actorRole': 'CUSTOMER'}],
                 'checkoutKey': key, 'requestHash': fingerprint, 'commerceVersion': 1,
                 'inventoryReserved': True, 'promotionReserved': bool(promo_code), 'promotionUsageAccounted': bool(promo_code)}
        db.orders.insert_one(order, session=session)
        cleared = db.carts.update_one({'_id': principal['_id'], 'customerCode': principal['customerCode'], 'version': quote['cartVersion']},
                                      {'$set': {'items': [], 'promoCode': '', 'updatedAt': now}, '$inc': {'version': 1}}, session=session)
        if cleared.modified_count != 1:
            raise ShoppingError('Giỏ vừa được sửa; hãy xác nhận lại', 'cart_conflict', 409)
        db.audit_logs.insert_one({'actorUserId': principal['_id'], 'action': 'orders.create', 'resourceType': 'orders',
                                  'resourceId': order_code, 'timestamp': now, 'result': 'success', 'metadata': {'status': 'pending'}}, session=session)
        return order

    try:
        return repo.transaction(commit)
    except DuplicateKeyError:
        existing = repo.existing_order(principal, key)
        if existing:
            return replay(existing, fingerprint)
        raise ShoppingError('Xung đột lần đặt hàng; vui lòng thử lại', 'idempotency_conflict', 409)


def safe_order(order):
    return {k: v for k, v in order.items() if k not in {'_id', 'checkoutKey', 'requestHash', 'inventoryReserved', 'promotionReserved', 'promotionUsageAccounted'}}
