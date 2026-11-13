import pytest
from services.access_policy import ROLE_PERMISSIONS, has_permission, REPORT_PERMISSIONS
from services.security import ENDPOINT_POLICIES


def test_every_endpoint_method_has_explicit_policy(app):
    for rule in app.url_map.iter_rules():
        for method in rule.methods - {'HEAD', 'OPTIONS'}:
            assert (rule.endpoint, method) in ENDPOINT_POLICIES, (rule, method)
    assert not has_permission({'role': 'ADMIN'}, 'undeclared.permission')


@pytest.mark.parametrize('role', list(ROLE_PERMISSIONS))
def test_role_endpoint_method_matrix(app, login_as, csrf, role, monkeypatch):
    """Exercise real session loading, route authorization and CSRF for every method.

    Business handlers are replaced AFTER login to isolate access control; additional
    integration tests below exercise the actual business handlers and ownership.
    """
    client = login_as(role)
    token = csrf(client)
    public = {ep for (ep, method), perm in ENDPOINT_POLICIES.items() if perm is None}
    for ep in app.view_functions:
        if ep not in public:
            monkeypatch.setitem(app.view_functions, ep, lambda **kwargs: ('', 204))
    for rule in app.url_map.iter_rules():
        for method in rule.methods - {'HEAD', 'OPTIONS'}:
            policy = ENDPOINT_POLICIES[(rule.endpoint, method)]
            if policy is None:
                continue
            path = str(rule).replace('<code>', 'UNKNOWN').replace('<user_id>', '000000000000000000000000')
            result = client.open(path, method=method, headers={'X-CSRF-Token': token})
            assert result.status_code == (204 if has_permission({'role': role}, policy) else 403), (role, path, method, result.status_code)


def test_guest_and_undeclared_endpoint(app):
    @app.get('/api/unregistered')
    def unregistered():
        return 'secret'
    c = app.test_client()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'unregistered':
            continue
        if ENDPOINT_POLICIES.get((rule.endpoint, 'GET')):
            path = str(rule).replace('<code>', 'UNKNOWN').replace('<user_id>', '000000000000000000000000')
            result = c.get(path)
            assert result.status_code == (401 if path.startswith('/api/') else 302), path
    assert c.get('/api/unregistered').status_code == 403


@pytest.mark.parametrize('code,permission', REPORT_PERMISSIONS.items())
def test_analyst_report_code_enforcement(login_as, code, permission):
    c = login_as('ANALYST')
    assert c.get('/bao-cao?report=' + code).status_code == (200 if permission == 'reports.read_aggregate' else 403)
    assert c.get('/bao-cao?report=UNKNOWN').status_code == 400


def test_analyst_dashboard_has_no_customer_details(login_as):
    c = login_as('ANALYST')
    assert 'NC10' not in c.get('/api/dashboard/ratings').json['data']
    assert 'NC04' not in c.get('/api/dashboard/sales').json['data']


def test_customer_ownership_and_forged_review(app, login_as, csrf):
    c = login_as('CUSTOMER', 'KHACHHANG20260002')
    assert c.get('/api/account/orders?customerCode=KHACHHANG20260001').json['data'] == []
    for path in ['/api/account/orders/DONHANG2026090001', '/account/orders/DONHANG2026090001']:
        assert c.get(path).status_code == 404
    assert c.get('/api/customers/KHACHHANG20260001').status_code == 403
    payload = {'productCode': 'SANPHAM2026090007', 'rating': 4, 'content': 'Review', 'customerCode': 'KHACHHANG20260001'}
    assert c.post('/api/reviews', json=payload, headers={'X-CSRF-Token': csrf(c)}).status_code == 400
    payload.pop('customerCode')
    result = c.post('/api/reviews', json=payload, headers={'X-CSRF-Token': csrf(c)})
    assert result.status_code == 400
    assert c.patch('/api/reviews/DANHGIA2026090001/status', json={'status': 'approved'}, headers={'X-CSRF-Token': csrf(c)}).status_code == 403


def test_admin_cannot_impersonate_and_customer_verified_purchase(client, login_as, csrf):
    data = {'productCode': 'SANPHAM2026090007', 'rating': 4, 'content': 'Review'}
    assert client.post('/api/reviews', json=data, headers={'X-CSRF-Token': csrf(client)}).status_code == 403
    c = login_as('CUSTOMER')
    row = c.post('/api/reviews', json=data, headers={'X-CSRF-Token': csrf(c)}).json['data']
    assert row['verifiedPurchase'] is True
    assert c.get('/api/account/reviews').status_code == 200


@pytest.mark.parametrize('target_role', [role for role in ROLE_PERMISSIONS if role != 'CUSTOMER'])
def test_account_manager_cannot_target_privileged_accounts(app, login_as, csrf, target_role):
    manager = login_as('ACCOUNT_MANAGER')
    login_as(target_role)
    target = app.extensions['mongo_db'].users.find_one({'role': target_role})
    path = '/admin/users/' + str(target['_id']) + '/edit'
    token = csrf(manager)
    assert manager.get(path).status_code == 404
    assert manager.post(path, data={'status': 'disabled', 'csrf_token': token}).status_code == 404
    result = manager.put('/api/users/' + str(target['_id']), json={'status': 'disabled'}, headers={'X-CSRF-Token': token})
    assert result.status_code == 404 and result.json['success'] is False
    assert app.extensions['mongo_db'].users.find_one({'_id': target['_id']})['status'] == 'active'


@pytest.mark.parametrize('role', [role for role in ROLE_PERMISSIONS if role != 'CUSTOMER'])
def test_account_manager_cannot_create_other_roles(app, login_as, csrf, account_password, role):
    manager = login_as('ACCOUNT_MANAGER')
    data = {'email': 'forged@example.test', 'role': role, 'password': account_password, 'customerCode': 'KHACHHANG20260001'}
    assert manager.post('/api/users', json=data, headers={'X-CSRF-Token': csrf(manager)}).status_code == 403
    assert manager.post('/admin/users/create', data={**data, 'csrf_token': csrf(manager)}).status_code == 403
    assert not app.extensions['mongo_db'].users.find_one({'emailNormalized': data['email']})


@pytest.mark.parametrize('payload', [{'role': 'CUSTOMER'}, {'role': 'ADMIN'}, {'role': 'ACCOUNT_MANAGER'},
                                     {'role': ''}, {'customerCode': ''},
                                     {'customerCode': 'KHACHHANG20260001'}, {'customerCode': 'KHACHHANG20260002'}, {'status': 'locked'}])
def test_account_manager_cannot_change_role_link_or_lock(app, login_as, csrf, payload):
    manager = login_as('ACCOUNT_MANAGER')
    login_as('CUSTOMER')
    target = app.extensions['mongo_db'].users.find_one({'role': 'CUSTOMER'})
    headers = {'X-CSRF-Token': csrf(manager)}
    assert manager.put('/api/users/' + str(target['_id']), json=payload, headers=headers).status_code == 403
    assert manager.post('/admin/users/' + str(target['_id']) + '/edit', data={**payload, 'csrf_token': csrf(manager)}).status_code == 403


def test_manager_list_scope_count_and_permissions(app, login_as):
    manager = login_as('ACCOUNT_MANAGER')
    login_as('PRODUCT_STAFF')
    login_as('CUSTOMER')
    login_as('CUSTOMER', 'KHACHHANG20260002')
    result = manager.get('/api/users?per_page=1')
    assert isinstance(result.json['data'], list)
    assert len(result.json['data']) == 1
    assert result.headers['X-Total-Count'] == '2'
    assert all(row['role'] == 'CUSTOMER' for row in result.json['data'])
    assert manager.get('/api/users?role=ADMIN').status_code == 403
    assert manager.get('/admin/users?role=ADMIN').status_code == 403
    assert manager.get('/api/users?status=disabled').headers['X-Total-Count'] == '0'
    html = manager.get('/admin/users').text
    assert 'Chỉ quản lý khách hàng' in html and 'admin@example.test' not in html
    assert 'account_manager@example.test' in html  # Own navbar identity only.
    for permission in ['users.read', 'users.create', 'users.update', 'users.disable', 'users.reset_password', 'account.change_own_password', 'account.logout']:
        assert has_permission({'role': 'ACCOUNT_MANAGER'}, permission)
    for permission in ['users.assign_role', 'users.manage_all', 'customers.read', 'reports.read_aggregate', 'products.update']:
        assert not has_permission({'role': 'ACCOUNT_MANAGER'}, permission)
