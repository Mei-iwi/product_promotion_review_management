from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import re
import mongomock
import pytest
from app import create_app
from db.mongo import get_db
from repositories import security_repository as store
from services import auth_service as auth, user_service, review_service
from services.helpers import ValidationError


def token_for(client):
    return re.search(r'name="csrf-token" content="([^"]+)"', client.get('/login').get_data(as_text=True))[1]


@pytest.mark.parametrize('role', [
    'ADMIN', 'ACCOUNT_MANAGER', 'PRODUCT_STAFF', 'MARKETING_STAFF',
    'SUPPORT_STAFF', 'REVIEW_MODERATOR', 'ANALYST', 'CUSTOMER',
])
def test_every_role_logs_in_to_catalog(app, login_as, account_password, role):
    client = login_as(role)
    with app.app_context():
        email = get_db().users.find_one({'role': role})['email']
    result = client.post('/login?next=https://evil.example', data={
        'email': email, 'password': account_password, 'csrf_token': token_for(client),
    })
    assert result.status_code == 302
    assert result.location == '/catalog'
    assert client.get(result.location).status_code == 200


def test_login_unknown_and_bad_password_same_response(app, client, account_password):
    c = app.test_client()
    token = token_for(c)
    one = c.post('/login', data={'email': 'unknown@example.test', 'password': 'wrong', 'csrf_token': token})
    two = c.post('/login', data={'email': 'admin@example.test', 'password': 'wrong', 'csrf_token': token})
    assert one.status_code == two.status_code == 401
    assert auth.LOGIN_ERROR in one.text and auth.LOGIN_ERROR in two.text


@pytest.mark.parametrize('status', ['disabled', 'locked'])
def test_cannot_login_disabled_locked(app, client, csrf, account_password, status):
    app.extensions['mongo_db'].users.update_one({'role': 'ADMIN'}, {'$set': {'status': status, 'lockedUntil': store.utcnow() + timedelta(minutes=15)}})
    c = app.test_client()
    result = c.post('/login', data={'email': 'admin@example.test', 'password': account_password, 'csrf_token': token_for(c)})
    assert result.status_code == 401
    assert client.get('/api/products').status_code == 401


def test_inactive_customer_loses_access_and_cannot_relogin(app, login_as, account_password):
    c = login_as('CUSTOMER')
    app.extensions['mongo_db'].customers.update_one({'customerCode': 'KHACHHANG20260001'}, {'$set': {'status': 'inactive'}})
    assert c.get('/api/account/profile').status_code == 401
    result = c.post('/login', data={'email': 'customer-KHACHHANG20260001@example.test', 'password': account_password, 'csrf_token': token_for(c)})
    assert result.status_code == 401


def test_logout_replay_and_fixation(app, login_as, csrf):
    c = app.test_client()
    token_for(c)
    cookie_name = app.config['AUTH_COOKIE_NAME']
    anonymous_cookie = c.get_cookie(cookie_name).value
    c = login_as('ADMIN', client=c)
    authenticated_cookie = c.get_cookie(cookie_name).value
    assert authenticated_cookie != anonymous_cookie
    attacker = app.test_client()
    attacker.set_cookie(cookie_name, anonymous_cookie)
    assert attacker.get('/api/products').status_code == 401
    assert c.post('/logout', data={'csrf_token': csrf(c)}).location == '/login'
    attacker.set_cookie(cookie_name, authenticated_cookie)
    assert attacker.get('/api/products').status_code == 401
    assert c.get_cookie(cookie_name) is None


@pytest.mark.parametrize('field', ['idleExpiresAt', 'absoluteExpiresAt'])
def test_http_session_expiration(app, client, field):
    db = app.extensions['mongo_db']
    db.sessions.update_many({'userId': {'$ne': None}}, {'$set': {field: store.utcnow() - timedelta(seconds=1)}})
    assert client.get('/api/products').status_code == 401


def test_change_password_revokes_other_browser(app, login_as, csrf, account_password):
    c = login_as('ADMIN')
    other = login_as('ADMIN')
    assert c.post('/account/change-password', data={'currentPassword': 'wrong', 'newPassword': 'new mountain river tulip evening', 'csrf_token': csrf(c)}).status_code == 400
    assert c.post('/account/change-password', data={'currentPassword': account_password, 'newPassword': 'new mountain river tulip evening', 'csrf_token': csrf(c)}).status_code == 302
    assert other.get('/api/products').status_code == 401


@pytest.mark.parametrize('method,path', [
    ('POST', '/api/products'), ('PUT', '/api/products/SANPHAM2026090007'),
    ('PATCH', '/api/products/SANPHAM2026090007/status'), ('DELETE', '/api/products/SANPHAM2026090007'),
    ('POST', '/logout'), ('POST', '/san-pham/them'), ('POST', '/admin/users/create'),
    ('POST', '/account/change-password'), ('POST', '/danh-gia/DANHGIA2026090001/trang-thai'),
])
def test_missing_wrong_csrf(client, method, path):
    assert client.open(path, method=method).status_code == 400
    assert client.open(path, method=method, headers={'X-CSRF-Token': 'wrong'}).status_code == 400


def test_login_csrf_is_required(app):
    c = app.test_client()
    assert c.post('/login', data={'email': 'x@example.test', 'password': 'wrong'}).status_code == 400
    token_for(c)
    assert c.post('/login', data={'csrf_token': 'không hợp lệ'}).status_code == 400


def test_role_change_disable_revoke_immediately(app, login_as, csrf, account_password):
    admin = login_as('ADMIN')
    staff = login_as('PRODUCT_STAFF')
    target = app.extensions['mongo_db'].users.find_one({'role': 'PRODUCT_STAFF'})
    url = '/api/users/' + str(target['_id'])
    assert admin.put(url, json={'role': 'ANALYST', 'actorPassword': account_password}, headers={'X-CSRF-Token': csrf(admin)}).status_code == 200
    assert staff.get('/api/products').status_code == 401
    # A fresh login uses the role read from MongoDB, independent of the old cookie.
    with app.app_context():
        token, _ = auth.issue_session(get_db().users.find_one({'_id': target['_id']}))
    staff.set_cookie(app.config['AUTH_COOKIE_NAME'], token)
    assert staff.get('/api/products').status_code == 403
    assert admin.put(url, json={'status': 'disabled', 'actorPassword': account_password}, headers={'X-CSRF-Token': csrf(admin)}).status_code == 200
    assert staff.get('/api/dashboard/summary').status_code == 401


def test_shared_session_store_two_apps(app, login_as):
    c = login_as('PRODUCT_STAFF')
    other_app = create_app({'TESTING': True, 'MONGO_DB': app.config['MONGO_DB'], 'SECRET_KEY': 'independent-worker-secret'}, app.extensions['mongo_client'])
    other = other_app.test_client()
    other.set_cookie(app.config['AUTH_COOKIE_NAME'], c.get_cookie(app.config['AUTH_COOKIE_NAME']).value)
    assert other.get('/api/products').status_code == 200


def test_last_admin_guard_reauth_and_concurrent_updates(app, login_as, account_password):
    login_as('ADMIN')
    with app.app_context():
        admin = get_db().users.find_one({'role': 'ADMIN'})
        with pytest.raises(ValidationError):
            user_service.update_user(admin, str(admin['_id']), {'status': 'disabled', 'actorPassword': account_password})
        with pytest.raises(ValidationError):
            auth.create_user({'email': 'other@example.test', 'role': 'ADMIN', 'password': account_password}, admin)
        second = auth.create_user({'email': 'other@example.test', 'role': 'ADMIN', 'password': account_password, 'actorPassword': account_password}, admin)
    def disable_self(actor):
        with app.app_context():
            try:
                user_service.update_user(actor, str(actor['_id']), {'status': 'disabled', 'actorPassword': account_password})
                return 'ok'
            except (ValidationError, BlockingIOError):
                return 'denied'
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(disable_self, [admin, second]))
    assert result.count('ok') == 1
    assert app.extensions['mongo_db'].users.count_documents({'role': 'ADMIN', 'status': 'active'}) == 1


@pytest.mark.parametrize('payload', [
    {'role': 'ADMIN'}, {'permissions': ['users.assign_role']}, {'authVersion': 999},
    {'customerCode': 'KHACHHANG20260002'}, {'fullName': {'$ne': None}},
])
def test_profile_mass_assignment_and_injection(login_as, csrf, payload):
    c = login_as('CUSTOMER')
    assert c.put('/api/account/profile', json=payload, headers={'X-CSRF-Token': csrf(c)}).status_code == 400


def test_no_operator_injection_or_product_delete_flag(app, client, csrf):
    from tests.test_application import product_payload
    for payload in [{'name': {'$ne': None}}, {'price': {'$gt': 0}}, {'status': {}}, {'createdByApp': True}]:
        data = product_payload('SANPHAM2026090007')
        data.update(payload)
        assert client.put('/api/products/SANPHAM2026090007', json=data, headers={'X-CSRF-Token': csrf(client)}).status_code == 400
    assert app.extensions['mongo_db'].products.find_one({'productCode': 'SANPHAM2026090007'}).get('createdByApp') is None
    assert client.delete('/api/products/SANPHAM2026090007', headers={'X-CSRF-Token': csrf(client)}).status_code == 400


@pytest.mark.parametrize('field,value', [('status', 'approved'), ('verifiedPurchase', True), ('helpfulCount', 999), ('createdAt', '2020-01-01')])
def test_review_server_fields_cannot_be_supplied(login_as, csrf, field, value):
    c = login_as('CUSTOMER')
    data = {'productCode': 'SANPHAM2026090007', 'rating': 4, 'content': 'Review', field: value}
    assert c.post('/api/reviews', json=data, headers={'X-CSRF-Token': csrf(c)}).status_code == 400


def test_moderator_cannot_self_moderate(app, login_as):
    login_as('REVIEW_MODERATOR')
    with app.app_context():
        moderator = get_db().users.find_one({'role': 'REVIEW_MODERATOR'})
        get_db().reviews.update_one({'reviewCode': 'DANHGIA2026090001'}, {'$set': {'createdByUserId': moderator['_id']}})
        from werkzeug.exceptions import Forbidden
        with pytest.raises(Forbidden):
            review_service.moderate(moderator, 'DANHGIA2026090001', 'approved')


def test_public_projection_and_xss(app, client, csrf):
    db = app.extensions['mongo_db']
    xss = '<script>alert("xss")</script>'
    db.products.update_one({'productCode': 'SANPHAM2026090007'}, {'$set': {'name': xss}})
    db.products.update_one({'productCode': 'SANPHAM2026090001'}, {'$set': {'status': 'inactive'}})
    db.reviews.update_one({'reviewCode': 'DANHGIA2026090001'}, {'$set': {'content': xss, 'status': 'pending'}})
    guest = app.test_client()
    products = guest.get('/api/public/products').json['data']
    assert len(products) == 1 and 'stock' not in products[0] and 'attributes' not in products[0]
    assert guest.get('/api/public/products/SANPHAM2026090007/reviews').json['data'] == []
    db.reviews.update_one({'reviewCode': 'DANHGIA2026090001'}, {'$set': {'status': 'approved'}})
    reviews = guest.get('/api/public/products/SANPHAM2026090007/reviews').json['data']
    assert not {'customer', 'customerCode', 'createdByUserId'} & set(reviews[0])
    html = guest.get('/catalog/SANPHAM2026090007').text
    assert xss not in html and '&lt;script&gt;' in html
    assert xss not in client.get('/san-pham?q=' + xss).text


def test_open_redirect_headers_cookie_and_no_secret_leak(app, login_as, csrf, account_password):
    c = app.test_client()
    token = token_for(c)
    result = c.post('/login?next=https://evil.example', data={'email': 'admin@example.test', 'password': account_password, 'csrf_token': token})
    # No account exists yet; create via the authenticated fixture then retry.
    c = login_as('ADMIN', client=c)
    result = c.post('/login?next=//evil.example', data={'email': 'admin@example.test', 'password': account_password, 'csrf_token': csrf(c)})
    assert result.location == '/catalog'
    cookie = result.headers.get('Set-Cookie')
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie and 'Path=/' in cookie
    assert c.get('/api/users').headers['X-Content-Type-Options'] == 'nosniff'
    assert "script-src 'self'" in c.get('/').headers['Content-Security-Policy']
    assert 'no-store' in c.get('/').headers['Cache-Control']
    assert 'Strict-Transport-Security' not in c.get('/').headers
    for path in ['/api/users', '/admin/users', '/admin/users/create']:
        text = c.get(path).text
        assert 'passwordHash' not in text and '$argon2id$' not in text
    logs = list(app.extensions['mongo_db'].audit_logs.find({}))
    serialized = json.dumps(logs, default=str)
    assert account_password not in serialized and 'csrfToken' not in serialized and 'sessionIdHash' not in serialized


def test_production_fails_fast_and_enforces_https():
    with pytest.raises(RuntimeError):
        create_app({'APP_ENV': 'production', 'SECRET_KEY': '', 'TESTING': True}, mongomock.MongoClient())
    import secrets
    app = create_app({'APP_ENV': 'production', 'SECRET_KEY': secrets.token_hex(32), 'TESTING': True}, mongomock.MongoClient())
    c = app.test_client()
    assert c.get('/catalog').status_code == 400
    result = c.get('/login', base_url='https://example.test')
    assert result.status_code == 200
    cookie = result.headers['Set-Cookie']
    assert '__Host-auth=' in cookie and 'Secure' in cookie and 'Domain=' not in cookie
    assert result.headers['Strict-Transport-Security'] == 'max-age=31536000'


def test_auth_pages_load_and_role_navigation(app, login_as):
    c = login_as('ADMIN')
    user = app.extensions['mongo_db'].users.find_one({'role': 'ADMIN'})
    for path in ['/admin/users', '/admin/users/create', '/admin/users/' + str(user['_id']) + '/edit', '/account/change-password']:
        assert c.get(path).status_code == 200
    c = login_as('CUSTOMER')
    for path in ['/account', '/account/orders', '/account/orders/DONHANG2026090001', '/account/reviews']:
        assert c.get(path).status_code == 200
    html = c.get('/account').text
    assert 'href="/admin/users"' not in html and 'href="/khach-hang"' not in html


def test_body_size_limit_and_json_errors(client):
    response = client.post('/api/products', data='x' * (1024 * 1024 + 1))
    assert response.status_code == 413
    assert set(response.json) == {'success', 'message', 'data'}
    assert client.get('/api/unknown').status_code == 404


def test_all_reports_regression_with_admin(client):
    for group, count in [('CB', 12), ('NC', 10)]:
        for i in range(1, count + 1):
            assert client.get('/bao-cao?report=' + f'{group}{i:02}').status_code == 200


def test_cli_bootstrap_interactive_once(app, account_password):
    runner = app.test_cli_runner()
    result = runner.invoke(args=['bootstrap-admin', '--email', 'bootstrap@example.test'], input=account_password + '\n' + account_password + '\n')
    assert result.exit_code == 0
    assert account_password not in result.output
    again = runner.invoke(args=['bootstrap-admin', '--email', 'another@example.test'], input=account_password + '\n' + account_password + '\n')
    assert again.exit_code != 0
    assert app.extensions['mongo_db'].users.count_documents({'role': 'ADMIN'}) == 1


def test_deactivate_customer_revokes_even_after_reactivation(app, login_as, client, csrf):
    c = login_as('CUSTOMER')
    data = {'fullName': 'Customer', 'email': 'anh@qlkm.local', 'address': 'address', 'level': 'normal', 'status': 'inactive'}
    assert client.put('/api/customers/KHACHHANG20260001', json=data, headers={'X-CSRF-Token': csrf(client)}).status_code == 200
    data['status'] = 'active'
    assert client.put('/api/customers/KHACHHANG20260001', json=data, headers={'X-CSRF-Token': csrf(client)}).status_code == 200
    assert c.get('/api/account/profile').status_code == 401


def test_real_business_http_crud_regression(client, login_as, csrf):
    from tests.test_application import product_payload
    code = 'SANPHAM2026100001'
    headers = {'X-CSRF-Token': csrf(client)}
    data = product_payload(code)
    assert client.post('/api/products', json=data, headers=headers).status_code == 201
    data['price'] = 999000
    assert client.put('/api/products/' + code, json=data, headers=headers).json['data']['price'] == 999000
    assert client.patch('/api/products/' + code + '/tags', json={'action': 'add', 'tag': 'demo'}, headers=headers).status_code == 200
    assert client.patch('/api/products/' + code + '/status', json={'status': 'inactive'}, headers=headers).status_code == 200
    assert client.delete('/api/products/' + code, headers=headers).status_code == 200
    promo = {'promoCode': 'DEMO2026', 'name': 'Promotion', 'promoType': 'percentage', 'value': 10, 'startDate': '2026-11-01', 'endDate': '2026-11-30', 'status': 'active'}
    assert client.post('/api/promotions', json=promo, headers=headers).status_code == 201
    promo['value'] = 20
    assert client.put('/api/promotions/DEMO2026', json=promo, headers=headers).json['data']['value'] == 20
    assert client.patch('/api/reviews/DANHGIA2026090001/status', json={'status': 'rejected'}, headers=headers).json['data']['status'] == 'rejected'
    assert client.patch('/api/reviews/DANHGIA2026090001/status', json={'status': 'approved'}, headers=headers).json['data']['status'] == 'approved'


def test_admin_account_http_create_reset_and_status(app, client, csrf, account_password):
    headers = {'X-CSRF-Token': csrf(client)}
    result = client.post('/api/users', json={'email': 'newstaff@example.test', 'password': account_password, 'role': 'PRODUCT_STAFF'}, headers=headers)
    assert result.status_code == 201
    assert result.json['data']['createdAt'].endswith('+07:00')
    url = '/api/users/' + result.json['data']['id']
    assert client.put(url, json={'password': 'updated fern violet river mountain'}, headers=headers).status_code == 400
    assert client.put(url, json={'password': 'updated fern violet river mountain', 'actorPassword': account_password}, headers=headers).status_code == 200
    assert client.put(url, json={'status': 'locked', 'actorPassword': account_password}, headers=headers).json['data']['status'] == 'locked'
    assert client.put(url, json={'status': 'active', 'actorPassword': account_password}, headers=headers).json['data']['status'] == 'active'
    assert client.put(url, json={'permissions': ['users.assign_role']}, headers=headers).status_code == 400


@pytest.mark.parametrize('password', ['short', '123456789012345', 'password123456789', 'aaaaaaaaaaaaaaaaaaaa', 'first first first first'])
def test_weak_password_rejected(password):
    with pytest.raises(ValidationError):
        auth.validate_password(password, 'first@example.test')


@pytest.mark.parametrize('path', ['/api/products?page=abc', '/api/products?min_price=oops', '/api/orders?from_date=bad', '/api/reviews?rating=abc'])
def test_invalid_filters_return_validation_error(client, path):
    assert client.get(path).status_code == 400


def test_admin_creates_and_manages_account_manager(app, client, csrf, account_password):
    headers = {'X-CSRF-Token': csrf(client)}
    data = {'email': 'manager@example.test', 'role': 'ACCOUNT_MANAGER', 'password': account_password}
    assert client.post('/api/users', json=data, headers=headers).status_code == 400
    data['actorPassword'] = 'incorrect'
    assert client.post('/api/users', json=data, headers=headers).status_code == 400
    data['actorPassword'] = account_password
    response = client.post('/api/users', json=data, headers=headers)
    assert response.status_code == 201
    target_id = response.json['data']['id']
    url = '/api/users/' + target_id
    assert client.put(url, json={'status': 'disabled'}, headers=headers).status_code == 400
    assert client.put(url, json={'status': 'disabled', 'actorPassword': account_password}, headers=headers).status_code == 200
    assert client.put(url, json={'status': 'active', 'actorPassword': account_password}, headers=headers).status_code == 200
    assert client.put(url, json={'role': 'ANALYST'}, headers=headers).status_code == 400
    assert client.put(url, json={'role': 'ANALYST', 'actorPassword': account_password}, headers=headers).status_code == 200
    assert client.put(url, json={'role': 'ACCOUNT_MANAGER'}, headers=headers).status_code == 400
    assert client.put(url, json={'role': 'ACCOUNT_MANAGER', 'actorPassword': account_password}, headers=headers).status_code == 200
    # Account managers also start at the catalog, retaining account-management access.
    c = app.test_client()
    result = c.post('/login', data={'email': data['email'], 'password': account_password, 'csrf_token': token_for(c)})
    assert result.location == '/catalog'
    assert c.get('/admin/users').status_code == 200


def test_manager_create_customer_web_api_and_duplicate_links(app, login_as, csrf, account_password):
    c = login_as('ACCOUNT_MANAGER')
    headers = {'X-CSRF-Token': csrf(c)}
    data = {'email': ' Customer.One@Example.Test ', 'password': account_password, 'customerCode': 'KHACHHANG20260001'}
    result = c.post('/api/users', json=data, headers=headers)
    assert result.status_code == 201
    assert result.json['data']['role'] == 'CUSTOMER'
    assert result.json['data']['email'] == 'customer.one@example.test'
    assert c.post('/api/users', json={**data, 'email': 'different@example.test'}, headers=headers).status_code == 400
    duplicate_email = {**data, 'customerCode': 'KHACHHANG20260002'}
    assert c.post('/api/users', json=duplicate_email, headers=headers).status_code == 400
    web_data = {**data, 'email': 'web.customer@example.test', 'customerCode': 'KHACHHANG20260002', 'role': 'CUSTOMER', 'csrf_token': csrf(c)}
    result = c.post('/admin/users/create', data=web_data, follow_redirects=True)
    assert result.status_code == 200 and 'Đã tạo tài khoản thành công' in result.text
    assert app.extensions['mongo_db'].users.find_one({'emailNormalized': web_data['email']})['role'] == 'CUSTOMER'


@pytest.mark.parametrize('code', ['', 'MISSING', 'KHACHHANG20260002'])
def test_manager_requires_active_existing_customer(app, login_as, csrf, account_password, code):
    c = login_as('ACCOUNT_MANAGER')
    app.extensions['mongo_db'].customers.update_one({'customerCode': 'KHACHHANG20260002'}, {'$set': {'status': 'inactive'}})
    result = c.post('/api/users', json={'email': 'new@example.test', 'password': account_password, 'customerCode': code}, headers={'X-CSRF-Token': csrf(c)})
    assert result.status_code == 400


@pytest.mark.parametrize('action', ['disable', 'unlock', 'reset'])
def test_manager_customer_lifecycle_revokes_sessions(app, login_as, csrf, account_password, action):
    manager = login_as('ACCOUNT_MANAGER')
    customer = login_as('CUSTOMER')
    other = login_as('CUSTOMER')
    db = app.extensions['mongo_db']
    user = db.users.find_one({'role': 'CUSTOMER'})
    before = user['authVersion']
    cookie_name = app.config['AUTH_COOKIE_NAME']
    old_cookie = customer.get_cookie(cookie_name).value
    payload = {'status': 'disabled'} if action == 'disable' else {'password': 'Replacement river candle mountain'}
    if action == 'unlock':
        db.users.update_one({'_id': user['_id']}, {'$set': {'status': 'locked', 'lockedUntil': store.utcnow() + timedelta(minutes=15), 'failedLoginCount': 5}})
        with app.app_context():
            for _ in range(5): store.reserve_attempt('account:' + auth.digest(user['emailNormalized']), 5)
        payload = {'status': 'active'}
    result = manager.put('/api/users/' + str(user['_id']), json=payload, headers={'X-CSRF-Token': csrf(manager)})
    assert result.status_code == 200
    assert db.users.find_one({'_id': user['_id']})['authVersion'] == before + 1
    assert customer.get('/api/account/profile').status_code == 401
    assert other.get('/api/account/profile').status_code == 401
    replay = app.test_client()
    replay.set_cookie(cookie_name, old_cookie)
    assert replay.get('/api/account/profile').status_code == 401
    if action == 'disable':
        assert manager.put('/api/users/' + str(user['_id']), json={'status': 'active'}, headers={'X-CSRF-Token': csrf(manager)}).status_code == 200
    password = payload.get('password', account_password)
    c = app.test_client()
    assert c.post('/login', data={'email': user['email'], 'password': password, 'csrf_token': token_for(c)}).status_code == 302
    if action == 'unlock':
        assert db.security_limits.find_one({'_id': 'account:' + auth.digest(user['emailNormalized'])}) is None


def test_manager_web_errors_keep_values_clear_passwords_and_csrf(app, login_as, csrf, account_password):
    c = login_as('ACCOUNT_MANAGER')
    html = c.get('/admin/users/create').text
    assert 'name="role"' not in html
    data = {'email': 'keep@example.test', 'customerCode': 'NOT_FOUND', 'password': account_password, 'actorPassword': account_password, 'csrf_token': csrf(c)}
    result = c.post('/admin/users/create', data=data)
    assert result.status_code == 400
    assert 'value="keep@example.test"' in result.text and 'value="NOT_FOUND"' in result.text
    assert account_password not in result.text and 'role="alert"' in result.text
    login_as('CUSTOMER')
    user = app.extensions['mongo_db'].users.find_one({'role': 'CUSTOMER'})
    edit = '/admin/users/' + str(user['_id']) + '/edit'
    html = c.get(edit).text
    assert 'name="customerCode"' not in html and 'name="role"' not in html
    assert 'data-account-edit' in html
    assert c.post('/api/users', json={'email': 'missingcsrf@example.test'}).status_code == 400
    assert c.put('/api/users/' + str(user['_id']), json={'status': 'disabled'}).status_code == 400
    assert c.post(edit, data={'status': 'disabled'}).status_code == 400


def test_account_filters_pagination_and_original_api_contract(app, login_as, csrf, account_password):
    c = login_as('ADMIN')
    db = app.extensions['mongo_db']
    with app.app_context():
        admin = db.users.find_one({'role': 'ADMIN'})
        for index in reversed(range(23)):
            auth.create_user({'email': f'page{index:02}@example.test', 'password': account_password, 'role': 'ANALYST'}, admin)
    all_rows = c.get('/api/users').json
    assert set(all_rows) == {'success', 'message', 'data'} and len(all_rows['data']) == 24
    path = '/api/users?q=PAGE&role=ANALYST&status=active&per_page=10'
    first, second, third = [c.get(path + '&page=' + str(page)) for page in [1, 2, 3]]
    assert [len(r.json['data']) for r in [first, second, third]] == [10, 10, 3]
    assert first.headers['X-Total-Count'] == '23'
    emails = [row['email'] for result in [first, second, third] for row in result.json['data']]
    assert emails == sorted(emails) and len(set(emails)) == 23
    html = c.get('/admin/users?q=PAGE&role=ANALYST&status=active&per_page=10').text
    assert 'page01@example.test' in html and 'page20@example.test' not in html
    from html import unescape
    from urllib.parse import parse_qs, urlsplit
    next_url = re.search(r'rel="next" href="([^"]+)"', html)[1]
    params = parse_qs(urlsplit(unescape(next_url)).query)
    assert params == {'q': ['PAGE'], 'role': ['ANALYST'], 'status': ['active'], 'per_page': ['10'], 'page': ['2']}
    assert c.get('/api/users?q=.*').json['data'] == []  # Literal search, never raw regex.
    assert c.get('/api/users?page=99999').json['data'] == []


@pytest.mark.parametrize('query', ['page=0', 'page=-1', 'page=1.5', 'page=100001', 'per_page=0', 'per_page=101',
                                  'role=INVALID', 'status=INVALID', 'permissions=x', 'sort=passwordHash',
                                  'q=' + 'x' * 255, 'role[$ne]=CUSTOMER', 'page=1&page=2'])
def test_account_filter_validation(client, query):
    for path in ['/api/users?', '/admin/users?']:
        result = client.get(path + query)
        assert result.status_code == 400


def test_account_scope_rechecked_inside_lock(app, login_as, account_password, monkeypatch):
    login_as('ACCOUNT_MANAGER')
    login_as('CUSTOMER')
    db = app.extensions['mongo_db']
    with app.app_context():
        actor = db.users.find_one({'role': 'ACCOUNT_MANAGER'})
        target = db.users.find_one({'role': 'CUSTOMER'})
        original = store.user_mutation_lock
        from contextlib import contextmanager
        @contextmanager
        def changed_target():
            with original():
                db.users.update_one({'_id': target['_id']}, {'$set': {'role': 'ANALYST'}})
                yield
        monkeypatch.setattr(store, 'user_mutation_lock', changed_target)
        from werkzeug.exceptions import NotFound, Forbidden
        with pytest.raises(NotFound):
            user_service.update_user(actor, str(target['_id']), {'status': 'disabled'})
        assert db.users.find_one({'_id': target['_id']})['status'] == 'active'
        @contextmanager
        def changed_actor():
            with original():
                db.users.update_one({'_id': actor['_id']}, {'$set': {'role': 'ANALYST'}})
                yield
        monkeypatch.setattr(store, 'user_mutation_lock', changed_actor)
        with pytest.raises(Forbidden):
            user_service.update_user(actor, str(target['_id']), {'status': 'disabled'})
        with pytest.raises(Forbidden):
            auth.create_user({'email': 'stale@example.test', 'customerCode': 'KHACHHANG20260002', 'password': account_password}, actor)


def test_manager_actions_are_audited_without_secrets(app, login_as, csrf, account_password):
    manager = login_as('ACCOUNT_MANAGER')
    data = {'email': 'audit.customer@example.test', 'customerCode': 'KHACHHANG20260001', 'password': account_password}
    result = manager.post('/api/users', json=data, headers={'X-CSRF-Token': csrf(manager)})
    assert result.status_code == 201
    target_id = result.json['data']['id']
    assert manager.put('/api/users/' + target_id, json={'status': 'disabled'}, headers={'X-CSRF-Token': csrf(manager)}).status_code == 200
    db = app.extensions['mongo_db']
    logs = list(db.audit_logs.find({'resourceId': target_id}).sort('timestamp', 1))
    actor = db.users.find_one({'role': 'ACCOUNT_MANAGER'})
    assert [log['action'] for log in logs] == ['users.create', 'users.update']
    assert all(log['actorUserId'] == actor['_id'] for log in logs)
    assert logs[-1]['metadata']['oldStatus'] == 'active' and logs[-1]['metadata']['status'] == 'disabled'
    text = json.dumps(logs, default=str)
    assert account_password not in text and 'passwordHash' not in text and 'csrfToken' not in text


def test_admin_customer_relink_and_last_admin_not_replaced_by_manager(app, client, login_as, csrf, account_password):
    login_as('ACCOUNT_MANAGER')
    login_as('CUSTOMER')
    db = app.extensions['mongo_db']
    target = db.users.find_one({'role': 'CUSTOMER'})
    headers = {'X-CSRF-Token': csrf(client)}
    assert client.put('/api/users/' + str(target['_id']), json={'customerCode': 'KHACHHANG20260002'}, headers=headers).status_code == 200
    admin = db.users.find_one({'role': 'ADMIN'})
    for changes in [{'status': 'disabled'}, {'status': 'locked'}, {'role': 'ACCOUNT_MANAGER'}]:
        result = client.put('/api/users/' + str(admin['_id']), json={**changes, 'actorPassword': account_password}, headers=headers)
        assert result.status_code == 400
        assert 'ADMIN' in result.json['message']
    assert db.users.find_one({'_id': admin['_id']})['role'] == 'ADMIN'


@pytest.mark.parametrize('filters', [{'q': {'$ne': ''}}, {'page': 1}, {'status': ['active']}, {'role': None}])
def test_account_filter_types_rejected(app, login_as, filters):
    login_as('ADMIN')
    with app.app_context():
        actor = get_db().users.find_one({'role': 'ADMIN'})
        with pytest.raises(ValidationError):
            user_service.list_users(actor, filters)
