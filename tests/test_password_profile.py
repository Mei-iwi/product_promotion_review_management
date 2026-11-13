import json

import pytest

from services import auth_service as auth

NEW = 'ocean violet lantern meadow trail'


@pytest.mark.parametrize('case', ['wrong-current', 'weak', 'same', 'mismatch', 'missing-confirm', 'missing-current'])
def test_password_invalid_inputs_never_change_hash_or_echo_secrets(app, login_as, csrf, account_password, case):
    client = login_as('CUSTOMER')
    db = app.extensions['mongo_db']
    before = db.users.find_one({'role': 'CUSTOMER'})
    data = {'currentPassword': account_password, 'newPassword': NEW, 'confirmPassword': NEW, 'csrf_token': csrf(client)}
    if case == 'wrong-current': data['currentPassword'] = 'incorrect phrase'
    if case == 'weak': data['newPassword'] = data['confirmPassword'] = '12345678'
    if case == 'same': data['newPassword'] = data['confirmPassword'] = account_password
    if case == 'mismatch': data['confirmPassword'] = NEW + ' different'
    if case == 'missing-confirm': data.pop('confirmPassword')
    if case == 'missing-current': data['currentPassword'] = ''
    reply = client.post('/account/change-password', data=data)
    assert reply.status_code == 400
    assert db.users.find_one({'_id': before['_id']})['passwordHash'] == before['passwordHash']
    assert NEW not in reply.text and account_password not in reply.text
    assert account_password not in json.dumps(list(db.audit_logs.find()), default=str)
    assert client.get('/account').status_code == 200


@pytest.mark.parametrize('json_reply', [False, True])
def test_password_success_reuses_service_revokes_all_cookies_and_requires_new_login(app, login_as, csrf, account_password, monkeypatch, json_reply):
    client = login_as('CUSTOMER')
    other = login_as('CUSTOMER')
    db = app.extensions['mongo_db']
    before = db.users.find_one({'role': 'CUSTOMER'})
    cookie_name = app.config['AUTH_COOKIE_NAME']
    old_cookie = client.get_cookie(cookie_name).value
    calls = []
    original = auth.change_password

    def spy(principal, current, new):
        calls.append(principal['_id'])
        return original(principal, current, new)

    monkeypatch.setattr(auth, 'change_password', spy)
    reply = client.post('/account/change-password', data={
        'csrf_token': csrf(client), 'currentPassword': account_password,
        'newPassword': NEW, 'confirmPassword': NEW,
    }, headers={'Accept': 'application/json'} if json_reply else {})
    assert calls == [before['_id']]
    assert reply.status_code == (200 if json_reply else 302)
    assert (reply.json['data']['redirect'] if json_reply else reply.location) == '/login'
    assert client.get_cookie(cookie_name) is None
    assert other.get('/api/account/profile').status_code == 401
    attacker = app.test_client()
    attacker.set_cookie(cookie_name, old_cookie)
    assert attacker.get('/api/account/profile').status_code == 401
    after = db.users.find_one({'_id': before['_id']})
    assert after['authVersion'] == before['authVersion'] + 1
    assert after['passwordHash'].startswith('$argon2id$')
    assert db.sessions.count_documents({'userId': before['_id'], 'revokedAt': None}) == 0
    login_page = client.get('/login')
    assert 'Đã đổi mật khẩu thành công' in login_page.text
    assert account_password not in login_page.text and NEW not in login_page.text
    with app.app_context():
        assert auth.authenticate(before['email'], account_password, 'password-old-test')[0] is None
        assert auth.authenticate(before['email'], NEW, 'password-new-test')[0]['_id'] == before['_id']
    logs = json.dumps(list(db.audit_logs.find()), default=str)
    assert NEW not in logs and account_password not in logs and 'passwordHash' not in logs


def test_password_mutation_requires_csrf_and_authenticated_session(app, login_as, csrf):
    data = {'currentPassword': 'something', 'newPassword': NEW, 'confirmPassword': NEW}
    assert app.test_client().post('/account/change-password', data=data).status_code == 302
    client = login_as('CUSTOMER')
    assert client.post('/account/change-password', data=data).status_code == 400
    assert client.post('/account/change-password', data={**data, 'csrf_token': 'wrong'}).status_code == 400


def test_password_form_still_available_to_staff(login_as):
    for role in ['ADMIN', 'PRODUCT_STAFF', 'ANALYST']:
        reply = login_as(role).get('/account/change-password')
        assert reply.status_code == 200
        assert 'name="confirmPassword"' in reply.text
        assert reply.text.count('data-password-toggle=') == 3


def test_checkout_phone_prefill_only_used_when_no_recipient_draft(app, login_as, monkeypatch):
    from services import checkout_service, promotion_offer_service
    client = login_as('CUSTOMER')
    db = app.extensions['mongo_db']
    db.customers.update_one({'customerCode': 'KHACHHANG20260001'}, {'$set': {'phone': '0912345678'}})
    quote = {'_id': 'test-key', 'lines': [], 'promoCode': '', 'subtotal': 0, 'discount': 0, 'total': 0, 'expiresAt': None}
    monkeypatch.setattr(checkout_service, 'get_quote', lambda *a: quote)
    monkeypatch.setattr(promotion_offer_service, 'for_cart', lambda *a: [])
    assert 'value="0912345678"' in client.get('/checkout/test-key').text
    with app.test_request_context('/checkout/test-key'):
        from flask import g
        from routes.shopping_routes import checkout_page
        g.current_user = db.users.find_one({'role': 'CUSTOMER'})
        g.auth_session = None
        html, _ = checkout_page('test-key', {'fullName': 'Đã nhập', 'address': 'Địa chỉ riêng', 'phone': '0987654321'})
        assert 'value="0987654321"' in html and 'value="0912345678"' not in html
