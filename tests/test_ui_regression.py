"""Presentation changes must retain permissions, user input and safe output."""
from html import unescape
import re
from urllib.parse import parse_qs, urlsplit

import pytest

from services.access_policy import ROLE_PERMISSIONS, has_permission


@pytest.mark.parametrize('role', list(ROLE_PERMISSIONS))
def test_sidebar_only_contains_permitted_destinations(login_as, role):
    client = login_as(role)
    destinations = {
        '/': 'reports.read_sensitive', '/san-pham': 'products.read_internal',
        '/khuyen-mai': 'promotions.read', '/khach-hang': 'customers.read',
        '/danh-gia': 'reviews.read_moderation_queue', '/don-hang': 'orders.read_all',
        '/thong-ke': 'reports.read_aggregate', '/bao-cao': 'reports.read_aggregate',
        '/admin/users': 'users.read',
    }
    permitted = [path for path, permission in destinations.items() if has_permission({'role': role}, permission)]
    if not permitted:
        assert 'id="admin-sidebar"' not in client.get('/catalog').text
        return
    html = client.get(permitted[0]).text
    sidebar = re.search(r'<aside id="admin-sidebar".*?</aside>', html, re.S)[0]
    links = re.findall(r'href="([^"]+)"', sidebar)
    for path, permission in destinations.items():
        assert (path in links) == has_permission({'role': role}, permission)


def test_admin_pagination_keeps_every_filter(client):
    html = client.get('/san-pham?brand=Apple&status=active&sort=price_desc&min_price=100&tag=test').text
    nav = re.search(r'<nav[^>]+aria-label="Phân trang sản phẩm quản trị".*?</nav>', html, re.S)[0]
    for href in re.findall(r'href="([^"]+)"', nav):
        args = parse_qs(urlsplit(unescape(href)).query)
        assert args['brand'] == ['Apple'] and args['status'] == ['active']
        assert args['sort'] == ['price_desc'] and args['min_price'] == ['100'] and args['tag'] == ['test']


@pytest.mark.parametrize('path,field,value', [
    ('/san-pham', 'status', 'inactive'), ('/khuyen-mai', 'promoType', 'fixed'),
    ('/khach-hang', 'level', 'gold'), ('/don-hang', 'status', 'cancelled'),
    ('/danh-gia', 'status', 'pending'),
])
def test_admin_filter_selection_survives_render(client, path, field, value):
    html = client.get(path, query_string={field: value}).text
    select = re.search(r'<select[^>]+name="' + field + r'".*?</select>', html, re.S)[0]
    assert f'<option value="{value}" selected>' in select


def test_invalid_product_form_retains_escaped_input_without_writing(client, app, csrf):
    data = {'csrf_token': csrf(client), 'productCode': 'UI-INVALID', 'name': '<script>bad()</script>',
            'brand': 'Test', 'categoryCode': 'TEST', 'categoryName': 'Test', 'price': '-1',
            'stock': '3', 'status': 'inactive', 'tags': 'one, two', 'attributes': 'color=mint'}
    response = client.post('/san-pham/them', data=data)
    assert response.status_code == 200
    assert 'value="&lt;script&gt;bad()&lt;/script&gt;"' in response.text
    assert 'value="-1"' in response.text and 'color=mint' in response.text
    assert '<option value="inactive" selected>' in response.text
    assert '<script>bad()</script>' not in response.text
    assert app.extensions['mongo_db'].products.find_one({'productCode': 'UI-INVALID'}) is None
