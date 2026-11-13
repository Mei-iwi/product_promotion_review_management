import pytest
from db.mongo import get_db


@pytest.mark.parametrize('status,allowed', [
    ('pending', False), ('cancelled', False), ('confirmed', True), ('completed', True),
])
def test_purchase_required_on_web_and_api(app, login_as, csrf, status, allowed):
    client = login_as('CUSTOMER')
    with app.app_context():
        db = get_db()
        db.orders.update_one({'orderCode': 'DONHANG2026090001'}, {'$set': {'status': status}})
        before = db.reviews.count_documents({})
    payload = {'productCode': 'SANPHAM2026090007', 'rating': 5, 'content': 'Sản phẩm rất tốt'}
    api = client.post('/api/reviews', json=payload, headers={'X-CSRF-Token': csrf(client)})
    web = client.post('/account/orders/DONHANG2026090001/reviews', data={**payload, 'csrf_token': csrf(client)})
    assert api.status_code == (201 if allowed else 400)
    assert web.status_code == (302 if allowed else 400)
    with app.app_context():
        assert get_db().reviews.count_documents({}) == before + (2 if allowed else 0)
        if allowed:
            assert api.json['data']['verifiedPurchase'] is True


def test_cannot_review_unbought_product_or_another_customers_purchase(app, login_as, csrf):
    client = login_as('CUSTOMER', customer='KHACHHANG20260002')
    for code in ['SANPHAM2026090001', 'SANPHAM2026090007']:
        payload = {'productCode': code, 'rating': 5, 'content': 'Sản phẩm tốt'}
        assert client.post('/api/reviews', json=payload, headers={'X-CSRF-Token': csrf(client)}).status_code == 400
        assert client.post('/account/orders/DONHANG2026090001/reviews', data={**payload, 'csrf_token': csrf(client)}).status_code == 404
        assert 'Đánh giá trong đơn hàng</a>' not in client.get('/catalog/' + code).text
    html = client.get('/account/reviews?productCode=SANPHAM2026090007').text
    assert 'name="productCode"' not in html
    assert 'Bạn chưa đánh giá sản phẩm nào' in html


def test_review_choices_only_purchased_products_and_account_dropdown(app, login_as):
    client = login_as('CUSTOMER')
    assert 'Đánh giá trong đơn hàng</a>' in client.get('/catalog/SANPHAM2026090007').text
    with app.app_context():
        get_db().products.update_one({'productCode': 'SANPHAM2026090007'}, {'$set': {'status': 'inactive'}})
    html = client.get('/account/reviews').text
    assert 'AirPods Pro thế hệ 2' in html
    assert 'name="productCode"' not in html and 'name="content"' not in html
    assert 'aria-label="Tài khoản khách hàng"' not in html
    for path in ['/account', '/account/reviews', '/account/change-password']:
        assert f'class="dropdown-item" href="{path}"' in html
    assert 'class="dropdown-item" href="/account/orders"' not in html
    assert 'href="/account/orders"' in html


def test_order_review_is_bound_to_order_and_preserves_invalid_form(app, login_as, csrf):
    client = login_as('CUSTOMER')
    path = '/account/orders/DONHANG2026090001/reviews'
    payload = {'productCode': 'SANPHAM2026090007', 'rating': '5', 'title': 'Đánh giá đã mua', 'content': 'Nội dung hợp lệ'}
    assert client.post(path, data=payload).status_code == 400
    assert client.post(path, data={**payload, 'productCode': 'SANPHAM2026090001', 'csrf_token': csrf(client)}).status_code == 400
    invalid = client.post(path, data={**payload, 'rating': '6', 'csrf_token': csrf(client)})
    assert invalid.status_code == 400 and 'Nội dung hợp lệ' in invalid.text and 'value="Đánh giá đã mua"' in invalid.text
    result = client.post(path, data={**payload, 'csrf_token': csrf(client)})
    assert result.status_code == 302 and result.location == '/account/orders/DONHANG2026090001'
    with app.app_context():
        row = get_db().reviews.find_one({'title': payload['title']})
        assert row['orderCode'] == 'DONHANG2026090001' and row['verifiedPurchase'] is True and row['status'] == 'pending'
        get_db().products.delete_one({'productCode': payload['productCode']})
    history = client.get('/account/reviews').text
    assert 'AirPods Pro thế hệ 2' in history and 'Nội dung hợp lệ' in history
    assert 'name="rating"' not in history and 'name="content"' not in history
    assert client.post('/account/reviews', data={**payload, 'csrf_token': csrf(client)}).status_code in {403, 404, 405}


def test_order_detail_forms_only_for_eligible_own_orders(app, login_as):
    client = login_as('CUSTOMER')
    for status, visible in [('pending', False), ('cancelled', False), ('confirmed', True), ('completed', True)]:
        with app.app_context():
            get_db().orders.update_one({'orderCode': 'DONHANG2026090001'}, {'$set': {'status': status}})
        html = client.get('/account/orders/DONHANG2026090001').text
        assert ('data-product-review' in html) is visible
