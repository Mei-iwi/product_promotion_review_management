from datetime import timedelta
import re
import pytest
from db.mongo import get_db
from repositories.security_repository import utcnow
from services import cart_service, checkout_service, promotion_offer_service


@pytest.fixture()
def offers(app):
    with app.app_context():
        db = get_db()
        now = utcnow()
        db.promotions.delete_many({})
        base = {'status': 'active', 'promoType': 'percentage', 'value': 10,
                'startDate': now - timedelta(days=1), 'endDate': now + timedelta(days=7),
                'conditions': {'minOrderValue': 0, 'maxDiscount': 100000},
                'targets': {'productCodes': ['SANPHAM2026090007'], 'categories': []}, 'usageLimit': 5}
        rows = [
            {**base, 'promoCode': 'GOOD10', 'name': 'Giảm mười phần trăm', 'privateAudit': 'PRIVATE-SECRET'},
            {**base, 'promoCode': 'BEST', 'name': 'Giảm hai trăm nghìn', 'promoType': 'fixed', 'value': 200000, 'conditions': {'minOrderValue': 0}},
            {**base, 'promoCode': 'MINIMUM', 'name': 'Đơn lớn', 'conditions': {'minOrderValue': 99999999}},
            {**base, 'promoCode': 'OTHER', 'name': 'Sản phẩm khác', 'targets': {'productCodes': ['SANPHAM2026090001']}},
            {**base, 'promoCode': 'FUTURE', 'name': 'Sắp bắt đầu', 'startDate': now + timedelta(days=1)},
            {**base, 'promoCode': 'EXHAUSTED', 'name': 'Đã dùng hết', 'commerceUsed': 5},
            {**base, 'promoCode': 'EXPIRED', 'name': 'Mã hết hạn', 'endDate': now - timedelta(days=1)},
            {**base, 'promoCode': 'DISABLED', 'name': 'Mã tắt', 'status': 'inactive'},
        ]
        db.promotions.insert_many(rows)
    return rows


def test_vouchers_require_login_and_private_fields_are_hidden(app, offers, login_as):
    guest = app.test_client()
    denied = guest.get('/vouchers')
    assert denied.status_code == 302 and '/login' in denied.location
    assert 'GOOD10' not in denied.text
    assert 'href="/vouchers"' not in guest.get('/catalog').text
    client = login_as('CUSTOMER')
    page = client.get('/vouchers')
    assert page.status_code == 200
    for text in ['GOOD10', 'FUTURE', 'EXHAUSTED']:
        assert text in page.text
    for text in ['EXPIRED', 'DISABLED', 'PRIVATE-SECRET', 'commerceUsed', 'Dùng mã này']:
        assert text not in page.text
    for query in ['page=0', 'page=x', 'page=1&page=2', 'role=ADMIN', 'page[$gt]=1']:
        assert client.get('/vouchers?' + query).status_code == 400
    with app.app_context():
        for i in range(15):
            get_db().promotions.insert_one({**offers[0], '_id': f'extra-{i}', 'promoCode': f'EXTRA{i:02}'})
    assert client.get('/vouchers?page=2').status_code == 200
    assert 'page=2' in client.get('/vouchers').text


def test_eligible_choices_use_actual_cart_and_do_not_consume_usage(app, offers, login_as, csrf):
    client = login_as('CUSTOMER')
    token = csrf(client)
    assert client.post('/cart/items', data={'productCode': 'SANPHAM2026090007', 'quantity': '1', 'csrf_token': token}).status_code == 302
    html = client.get('/cart').text
    assert 'value="BEST"' in html and 'value="GOOD10"' in html
    for code in ['MINIMUM', 'OTHER', 'FUTURE', 'EXHAUSTED', 'EXPIRED', 'DISABLED']:
        assert f'value="{code}"' not in html
    assert html.index('value="BEST"') < html.index('value="GOOD10"')
    assert 'Dùng mã này' in client.get('/vouchers').text
    assert client.post('/cart/promotion', data={'promoCode': 'BEST'}).status_code == 400
    assert client.post('/cart/promotion', data={'promoCode': 'BEST', 'csrf_token': token}).status_code == 302
    assert client.get('/api/account/cart').json['data']['discount'] == 200000
    assert client.post('/cart/promotion', data={'promoCode': '', 'csrf_token': token}).status_code == 302
    with app.app_context():
        assert get_db().promotions.find_one({'promoCode': 'BEST'}).get('commerceUsed', 0) == 0
        user = get_db().users.find_one({'role': 'CUSTOMER'})
        cart_service.change(user, 'apply', promo_code='GOOD10')
        # A stale selected code cannot prevent suggesting replacements.
        get_db().promotions.update_one({'promoCode': 'GOOD10'}, {'$set': {'commerceUsed': 5}})
        assert [r['promoCode'] for r in promotion_offer_service.for_cart(user)] == ['BEST']


def test_checkout_change_code_requires_reconfirmation_and_keeps_recipient(app, offers, login_as, csrf, monkeypatch):
    client = login_as('CUSTOMER')
    monkeypatch.setattr(checkout_service, 'require_ready', lambda: None)
    with app.app_context():
        user = get_db().users.find_one({'role': 'CUSTOMER'})
        cart_service.change(user, 'add', 'SANPHAM2026090007', 1)
        old = checkout_service.create_quote(user)
    data = {'fullName': 'Khách hàng', 'address': '123 Đường Demo', 'phone': '0901234567', 'promoCode': 'BEST', 'csrf_token': csrf(client)}
    path = '/checkout/' + old['_id'] + '/promotion'
    assert client.post(path, data={k: v for k, v in data.items() if k != 'csrf_token'}).status_code == 400
    changed = client.post(path, data=data)
    assert changed.status_code == 200
    assert 'value="123 Đường Demo"' in changed.text
    new_key = re.search(r'action="/checkout/([A-Za-z0-9_-]+)"', changed.text)[1]
    assert new_key != old['_id']
    with app.app_context():
        quote = checkout_service.get_quote(user, new_key)
        assert quote['discount'] == 200000
        assert quote['total'] == quote['subtotal'] - 200000
        assert get_db().orders.count_documents({}) == 1  # Existing fixture only.
    # Selecting another code cannot silently place an order at the previous total.
    assert client.post('/checkout/' + new_key, data={**data, 'promoCode': 'GOOD10'}).status_code == 400
    assert client.post(path, data=data).status_code == 409
    other = login_as('CUSTOMER', customer='KHACHHANG20260002')
    assert other.post('/checkout/' + new_key + '/promotion', data={**data, 'csrf_token': csrf(other)}).status_code == 404
