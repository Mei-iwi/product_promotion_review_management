from io import BytesIO
import json
import os

from PIL import Image
import pytest
from werkzeug.exceptions import Forbidden

from db.mongo import get_db
from services import account_profile_service, avatar_service
from services.access_policy import ROLE_PERMISSIONS, has_permission

STAFF = [role for role in ROLE_PERMISSIONS if role != 'CUSTOMER']


def image(color):
    output = BytesIO()
    Image.new('RGB', (60, 80), color).save(output, 'PNG')
    return output.getvalue()


@pytest.mark.parametrize('role', STAFF)
def test_every_staff_role_has_private_profile_without_customer_business_access(app, login_as, csrf, role):
    client = login_as(role)
    db = app.extensions['mongo_db']
    before = db.users.find_one({'role': role})
    customers_before = list(db.customers.find())
    html = client.get('/account').text
    assert 'id="profile-form"' in html and 'id="password-form"' in html
    assert 'id="avatar-pick"' in html and '>Vai trò</label>' in html
    assert 'Hạng thành viên' not in html and 'customerCode' not in html
    assert 'href="/account"' in client.get('/catalog').text
    assert '/account/change-password' not in client.get('/catalog').text
    data = {'fullName': 'Tên riêng ' + role, 'phone': '0912345678', 'dateOfBirth': '2000-01-02',
            'gender': 'undisclosed', 'address': 'Địa chỉ riêng', 'bio': 'Thông tin cá nhân'}
    reply = client.put('/api/account/profile', json=data, headers={'X-CSRF-Token': csrf(client)})
    assert reply.status_code == 200
    after = db.users.find_one({'_id': before['_id']})
    assert after['profile'] == data
    for key, value in before.items():
        assert after[key] == value
    assert list(db.customers.find()) == customers_before
    assert 'customerCode' not in after
    public = client.get('/api/account/profile').json['data']
    assert public['email'] == before['email'] and public['fullName'] == data['fullName']
    assert not {'passwordHash', 'authVersion', '_id', 'emailNormalized', 'failedLoginCount'} & set(public)
    assert before['passwordHash'] not in json.dumps(public)
    # Own-profile permissions do not add CUSTOMER permissions to any staff role.
    assert not has_permission({'role': role}, 'customers.read_own')
    assert not has_permission({'role': role}, 'cart.read_own')
    assert client.get('/cart').status_code == 403
    assert client.get('/account/orders').status_code == 403
    assert client.get('/account/reviews').status_code == 403


@pytest.mark.parametrize('field', ['role', 'email', 'status', 'authVersion', 'passwordHash', 'customerCode', 'level', 'profile', '_id', 'userId', 'avatar'])
def test_staff_profile_blocks_mass_assignment(app, login_as, csrf, field):
    client = login_as('PRODUCT_STAFF')
    before = app.extensions['mongo_db'].users.find_one({'role': 'PRODUCT_STAFF'})
    reply = client.put('/api/account/profile', json={field: 'injected'}, headers={'X-CSRF-Token': csrf(client)})
    assert reply.status_code == 400
    assert app.extensions['mongo_db'].users.find_one({'_id': before['_id']}) == before


def test_staff_partial_update_clear_validation_and_csrf(app, login_as, csrf):
    client = login_as('ANALYST')
    token = csrf(client)
    assert client.post('/account/profile', data={'fullName': 'Tên mới'}).status_code == 400
    assert client.put('/api/account/profile', json={'fullName': 'Tên mới', 'bio': 'Giữ lại'}, headers={'X-CSRF-Token': token}).status_code == 200
    assert client.put('/api/account/profile', json={'phone': '+84912345678'}, headers={'X-CSRF-Token': token}).status_code == 200
    assert client.put('/api/account/profile', json={'phone': ''}, headers={'X-CSRF-Token': token}).status_code == 200
    stored = app.extensions['mongo_db'].users.find_one({'role': 'ANALYST'})['profile']
    assert stored == {'fullName': 'Tên mới', 'bio': 'Giữ lại'}
    for data in [{'fullName': ''}, {'phone': 'invalid'}, {'dateOfBirth': '9999-01-01'}, {'gender': 'fake'}]:
        assert client.put('/api/account/profile', json=data, headers={'X-CSRF-Token': token}).status_code == 400


def test_avatars_are_separate_for_staff_customer_and_each_user(app, login_as, csrf, tmp_path):
    app.config['AVATAR_STORAGE_DIR'] = str(tmp_path)
    admin, analyst, customer = login_as('ADMIN'), login_as('ANALYST'), login_as('CUSTOMER')
    for client, color in [(admin, 'red'), (analyst, 'blue'), (customer, 'green')]:
        reply = client.post('/account/avatar', data={'csrf_token': csrf(client), 'avatar': (BytesIO(image(color)), 'photo.png')})
        assert reply.status_code == 302
    content = [client.get('/account/avatar').data for client in (admin, analyst, customer)]
    assert len(set(content)) == 3
    db = app.extensions['mongo_db']
    admin_key = db.users.find_one({'role': 'ADMIN'})['profile']['avatar']['key']
    analyst_key = db.users.find_one({'role': 'ANALYST'})['profile']['avatar']['key']
    for key in [admin_key, analyst_key]:
        os.utime(tmp_path / key, (1, 1))
    orphan = tmp_path / ('c' * 64 + '.webp')
    orphan.write_bytes(b'orphan')
    os.utime(orphan, (1, 1))
    assert app.test_cli_runner().invoke(args=['cleanup-avatar-orphans', '--apply']).exit_code == 0
    assert (tmp_path / admin_key).exists() and (tmp_path / analyst_key).exists() and not orphan.exists()
    assert admin.get('/account/avatar?userId=another').data == content[0]
    assert admin.post('/account/avatar/delete', data={'csrf_token': csrf(admin), 'userId': str(db.users.find_one({'role': 'ANALYST'})['_id'])}).status_code == 400
    assert admin.post('/account/avatar/delete', data={'csrf_token': csrf(admin)}).status_code == 302
    assert admin.get('/account/avatar').mimetype == 'image/svg+xml'
    assert analyst.get('/account/avatar').data == content[1]
    assert customer.get('/account/avatar').data == content[2]


def test_stale_or_disabled_staff_cannot_write_profile_or_avatar(app, login_as, csrf, tmp_path):
    app.config['AVATAR_STORAGE_DIR'] = str(tmp_path)
    client = login_as('SUPPORT_STAFF')
    db = app.extensions['mongo_db']
    old = db.users.find_one({'role': 'SUPPORT_STAFF'})
    db.users.update_one({'_id': old['_id']}, {'$inc': {'authVersion': 1}})
    with app.app_context():
        with pytest.raises(Forbidden):
            account_profile_service.update_profile(old, {'fullName': 'stale'})
        from werkzeug.datastructures import FileStorage
        with pytest.raises(Forbidden):
            avatar_service.replace(old, FileStorage(stream=BytesIO(image('red')), filename='portrait.png'))
        assert not list(tmp_path.iterdir())
    assert client.get('/account').status_code == 302
    assert 'profile' not in db.users.find_one({'_id': old['_id']})
