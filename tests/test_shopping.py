from copy import deepcopy
from datetime import datetime, timedelta, timezone
import re
import secrets
import pytest
from services import cart_service, checkout_service, promotion_service
from services.promotion_pricing import calculate
from services.shopping_common import ShoppingError
from repositories import shopping_repository

NOW = datetime(2026, 11, 11, 5, tzinfo=timezone.utc)


def promotion(**changes):
    row = {'promoCode': 'DEMO', 'status': 'active', 'promoType': 'percentage', 'value': 10,
           'startDate': NOW - timedelta(days=1), 'endDate': NOW + timedelta(days=1),
           'conditions': {'minOrderValue': 700000, 'maxDiscount': 40000},
           'targets': {'productCodes': ['P1'], 'categories': ['C1']}, 'usageLimit': 20, 'commerceUsed': 0}
    return {**row, **changes}


LINES = [{'productCode': 'P1', 'categoryCode': 'C1', 'lineTotal': 500000},
         {'productCode': 'P2', 'categoryCode': 'C2', 'lineTotal': 300000}]


def test_promotion_mixed_cart_example_and_or_not_double_counted():
    assert calculate(promotion(), LINES, 800000, NOW) == 40000
    unlimited = promotion(conditions={'minOrderValue': 700000, 'maxDiscount': 0})
    assert calculate(unlimited, LINES, 800000, NOW) == 50000


@pytest.mark.parametrize('promo,expected', [
    (promotion(promoType='fixed', value=600000, conditions={'minOrderValue': 0, 'maxDiscount': 0}), 500000),
    (promotion(promoType='fixed', value=100000, targets={'productCodes': [], 'categories': []}), 40000),
    (promotion(targets={'productCodes': [], 'categories': []}, conditions={'minOrderValue': 0, 'maxDiscount': 0}), 80000),
    (promotion(usageLimit=0, commerceUsed=999999), 40000),
])
def test_promotion_types_caps_and_unlimited(promo, expected):
    assert calculate(promo, LINES, 800000, NOW) == expected


def test_promotion_round_half_up_to_dong():
    promo = promotion(value=50, conditions={'minOrderValue': 0, 'maxDiscount': 0})
    lines = [{'productCode': 'P1', 'categoryCode': 'C1', 'lineTotal': 101}]
    assert calculate(promo, lines, 101, NOW) == 51


@pytest.mark.parametrize('changes,code', [
    ({'status': 'inactive'}, 'promo_inactive'), ({'status': 'expired'}, 'promo_expired'),
    ({'startDate': NOW + timedelta(microseconds=1)}, 'promo_not_started'),
    ({'endDate': NOW - timedelta(microseconds=1)}, 'promo_expired'),
    ({'commerceUsed': 20}, 'promo_exhausted'),
    ({'conditions': {'minOrderValue': 800001}}, 'promo_minimum'),
    ({'targets': {'productCodes': ['OTHER'], 'categories': ['NONE']}}, 'promo_no_eligible'),
])
def test_promotion_failures(changes, code):
    with pytest.raises(ShoppingError) as error:
        calculate(promotion(**changes), LINES, 800000, NOW)
    assert error.value.code == code


def test_promotion_utc_boundaries_and_missing():
    assert calculate(promotion(startDate=NOW, endDate=NOW), LINES, 800000, NOW) == 40000
    assert calculate(promotion(startDate=NOW.replace(tzinfo=None), endDate=NOW), LINES, 800000, NOW) == 40000
    with pytest.raises(ShoppingError) as error:
        calculate(None, LINES, 800000, NOW)
    assert error.value.code == 'promo_not_found'


def test_admin_promotion_date_roundtrip_vietnam(app):
    value = promotion_service.admin_date('2026-11-11T12:00', 'startDate')
    assert value == datetime(2026, 11, 11, 5)
    with app.app_context():
        shown = app.jinja_env.filters['datetime_local'](value)
        assert shown == '2026-11-11T12:00'
        assert promotion_service.admin_date(shown, 'startDate') == value
    assert promotion_service.admin_date('2026-11-11T05:00:00Z', 'startDate') == value


def test_catalog_search_filters_pagination_and_privacy(app, client):
    db = app.extensions['mongo_db']
    db.products.update_one({'productCode': 'SANPHAM2026090007'}, {'$set': {'stock': 0, 'internalCost': 12345,
                          'attributes': {'storage': '128GB', 'supplierPassword': 'hidden'}, 'image': 'javascript:alert(1)'}})
    guest = app.test_client()
    response = guest.get('/catalog?brand=Apple&sort=price_desc&per_page=1')
    assert response.status_code == 200
    from html import unescape
    from urllib.parse import urlsplit, parse_qs
    next_link = re.search(r'rel="next" href="([^"]+)"', response.text)[1]
    params = parse_qs(urlsplit(unescape(next_link)).query)
    assert params['brand'] == ['Apple'] and params['sort'] == ['price_desc'] and params['page'] == ['2']
    rows = guest.get('/api/public/products?q=AirPods').json['data']
    assert len(rows) == 1 and rows[0]['inStock'] is False
    assert rows[0]['image'] == '/static/img/product-placeholder.svg'
    assert not {'stock', 'internalCost', 'attributes'} & set(rows[0])
    html = guest.get('/catalog/SANPHAM2026090007').text
    assert '128GB' in html and 'supplierPassword' not in html and 'hidden' not in html.replace('type="hidden"', '')
    assert 'Hết hàng' in html and 'name="quantity"' not in html
    assert guest.get('/api/public/products?q=.*').json['data'] == []
    for query in ['page=0', 'per_page=49', 'sort=stock', 'status=inactive', 'brand[$ne]=x', 'q=' + 'x' * 101]:
        assert guest.get('/catalog?' + query).status_code == 400


def test_cart_persists_and_merges_without_cross_account_access(app, login_as, csrf):
    c = login_as('CUSTOMER')
    headers = {'X-CSRF-Token': csrf(c)}
    for _ in range(2):
        assert c.post('/api/account/cart/items', json={'productCode': 'SANPHAM2026090007', 'quantity': 1}, headers=headers).status_code == 200
    assert c.get('/api/account/cart').json['data']['items'] == [{'productCode': 'SANPHAM2026090007', 'quantity': 2}]
    c.post('/logout', data={'csrf_token': csrf(c)})
    c = login_as('CUSTOMER', client=c)
    assert c.get('/api/account/cart').json['data']['lines'][0]['quantity'] == 2
    other = login_as('CUSTOMER', 'KHACHHANG20260002')
    assert other.get('/api/account/cart?customerCode=KHACHHANG20260001').json['data']['items'] == []
    assert c.put('/api/account/cart/items/SANPHAM2026090007', json={'quantity': 3}, headers={'X-CSRF-Token': csrf(c)}).status_code == 200
    assert c.delete('/api/account/cart/items/SANPHAM2026090007', headers={'X-CSRF-Token': csrf(c)}).status_code == 200
    assert c.get('/api/account/cart').json['data']['items'] == []


@pytest.mark.parametrize('quantity', [0, -1, 100, True, 1.5, '1.0', {}, None])
def test_cart_bad_quantities(login_as, csrf, quantity):
    c = login_as('CUSTOMER')
    assert c.post('/api/account/cart/items', json={'productCode': 'SANPHAM2026090007', 'quantity': quantity}, headers={'X-CSRF-Token': csrf(c)}).status_code == 400


def test_cart_limit_stock_and_preview_does_not_reserve(app, login_as, csrf, monkeypatch):
    c = login_as('CUSTOMER')
    headers = {'X-CSRF-Token': csrf(c)}
    db = app.extensions['mongo_db']
    db.promotions.update_one({'promoCode': 'KHUYENMAI2026090001'}, {'$set': {'startDate': datetime(2020, 1, 1), 'endDate': datetime(2099, 1, 1), 'commerceUsed': 0}})
    monkeypatch.setattr(cart_service, 'MAX_LINES', 1)
    assert c.post('/api/account/cart/items', json={'productCode': 'SANPHAM2026090007', 'quantity': 1}, headers=headers).status_code == 200
    assert c.post('/api/account/cart/items', json={'productCode': 'SANPHAM2026090001', 'quantity': 1}, headers=headers).status_code == 400
    assert c.put('/api/account/cart/promotion', json={'promoCode': 'KHUYENMAI2026090001'}, headers=headers).status_code == 200
    assert db.promotions.find_one({'promoCode': 'KHUYENMAI2026090001'})['commerceUsed'] == 0
    assert db.products.find_one({'productCode': 'SANPHAM2026090007'})['stock'] == 40
    db.products.update_one({'productCode': 'SANPHAM2026090007'}, {'$set': {'status': 'inactive'}})
    assert c.get('/cart').status_code == 200
    assert c.get('/api/account/cart').json['data']['error']
    assert c.delete('/api/account/cart/items/SANPHAM2026090007', headers=headers).status_code == 200


def test_standalone_checkout_no_partial_writes(app, login_as, csrf):
    c = login_as('CUSTOMER')
    app.config['CHECKOUT_ENABLED'] = True
    headers = {'X-CSRF-Token': csrf(c)}
    db = app.extensions['mongo_db']
    before = {name: list(db[name].find({})) for name in ['orders', 'products', 'promotions', 'carts']}
    assert c.post('/api/account/checkout/quotes', json={}, headers=headers).status_code == 503
    assert c.post('/api/account/checkout', json={'checkoutKey': secrets.token_urlsafe(32), 'fullName': 'Khách thử', 'address': 'Số 12 đường Demo', 'phone': '0901234567'}, headers=headers).status_code == 503
    for name, docs in before.items():
        assert list(db[name].find({})) == docs


def test_shopping_ownership_csrf_and_review_prefill(app, login_as, csrf):
    c = login_as('CUSTOMER', 'KHACHHANG20260002')
    headers = {'X-CSRF-Token': csrf(c)}
    assert c.post('/api/account/orders/DONHANG2026090001/cancel', json={}, headers=headers).status_code == 404
    assert c.get('/account/orders/DONHANG2026090001/confirmation').status_code == 404
    assert c.post('/cart/items', data={'productCode': 'SANPHAM2026090007', 'quantity': 1}).status_code == 400
    assert c.post('/api/account/checkout/quotes', json={}).status_code == 400
    assert c.patch('/api/orders/DONHANG2026090001/status', json={'status': 'confirmed'}, headers=headers).status_code == 403
    assert c.post('/api/account/cart/items', json={'productCode': 'SANPHAM2026090007', 'quantity': 1, 'customerCode': 'KHACHHANG20260001'}, headers=headers).status_code == 400
    html = c.get('/account/reviews?productCode=SANPHAM2026090007').text
    assert 'value="SANPHAM2026090007"' not in html
    purchased = login_as('CUSTOMER')
    assert 'data-product-review' in purchased.get('/account/orders/DONHANG2026090001').text
    assert c.get('/account/orders?status=invalid').status_code == 400
    for data in [{'rating': 4, 'content': 'x' * 5001}, {'rating': 4, 'content': 'Review', 'title': 'x' * 201}]:
        assert c.post('/api/reviews', json={'productCode': 'SANPHAM2026090007', **data}, headers=headers).status_code == 400


def test_legacy_order_details_still_render(login_as):
    c = login_as('CUSTOMER')
    html = c.get('/account/orders/DONHANG2026090001').text
    assert 'Đơn cũ chưa lưu thông tin người nhận' in html
    assert 'Đơn cũ chưa lưu lịch sử' in html
    assert 'href="#review-1"' in html
