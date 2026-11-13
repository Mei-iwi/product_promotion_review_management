from io import BytesIO
from pathlib import Path
import os

from PIL import Image
from pymongo.errors import PyMongoError
import pytest

from repositories import security_repository as store
from services import avatar_service
from services.helpers import ValidationError


@pytest.fixture()
def avatar_directory(app, tmp_path):
    app.config['AVATAR_STORAGE_DIR'] = str(tmp_path / 'avatars')
    return Path(app.config['AVATAR_STORAGE_DIR'])


def picture(kind='PNG', size=(800, 600), color='teal', exif=None):
    stream = BytesIO()
    image = Image.new('RGB', size, color)
    image.save(stream, kind, **({'exif': exif} if exif else {}))
    return stream.getvalue()


def upload(client, csrf, content=None, filename='portrait.png', **fields):
    return client.post('/account/avatar', data={
        'csrf_token': csrf(client), 'avatar': (BytesIO(content if content is not None else picture()), filename), **fields,
    }, headers={'Accept': 'application/json'})


def test_account_legacy_profile_uses_login_email_and_never_renders_customer_code(app, login_as):
    client = login_as('CUSTOMER')
    db = app.extensions['mongo_db']
    db.users.update_one({'role': 'CUSTOMER'}, {'$set': {'email': 'login@example.test', 'emailNormalized': 'login@example.test'}})
    html = client.get('/account').text
    assert 'KHACHHANG20260001' not in html and 'customerCode' not in html
    assert 'login@example.test' in html and 'anh@qlkm.local' not in html
    assert 'confirmPassword' in html and 'data-async-form' in html
    assert 'account-tabs' not in html
    assert client.get('/account/avatar').mimetype == 'image/svg+xml'


@pytest.mark.parametrize('field,value,expected', [
    ('fullName', '  Tên mới  ', 'Tên mới'), ('phone', '+84 912-345-678', '+84912345678'),
    ('phone', '024 1234 5678', '02412345678'), ('dateOfBirth', '2000-02-29', '2000-02-29'),
    ('gender', 'undisclosed', 'undisclosed'), ('bio', '  Một chút về tôi  ', 'Một chút về tôi'),
    ('address', '  Địa chỉ mới  ', 'Địa chỉ mới'),
])
def test_profile_patch_updates_only_sent_field(app, login_as, csrf, field, value, expected):
    client = login_as('CUSTOMER')
    db = app.extensions['mongo_db']
    old = db.customers.find_one({'customerCode': 'KHACHHANG20260001'})
    result = client.put('/api/account/profile', json={field: value}, headers={'X-CSRF-Token': csrf(client)})
    assert result.status_code == 200
    current = db.customers.find_one({'_id': old['_id']})
    assert current[field] == expected
    for key, item in old.items():
        if key != field:
            assert current[key] == item
    assert db.users.find_one({'role': 'CUSTOMER'})['role'] == 'CUSTOMER'


@pytest.mark.parametrize('field,value', [
    ('fullName', ''), ('fullName', 'x' * 201), ('address', 'x' * 501), ('bio', 'x' * 301),
    ('phone', '1234567890'), ('phone', '+1234567890'), ('phone', '0912abc678'),
    ('phone', {'$ne': ''}), ('phone', None), ('dateOfBirth', '2001-02-29'),
    ('dateOfBirth', '9999-12-31'), ('dateOfBirth', '20000101'), ('gender', 'invalid'),
    ('email', 'forged@example.test'), ('level', 'gold'), ('avatar', {'key': '../other'}),
    ('role', 'ADMIN'), ('status', 'disabled'), ('passwordHash', 'fake'), ('authVersion', '99'),
    ('customerCode', 'KHACHHANG20260002'),
])
def test_profile_invalid_or_privileged_field_is_rejected_without_writing(app, login_as, csrf, field, value):
    client = login_as('CUSTOMER')
    db = app.extensions['mongo_db']
    before = db.customers.find_one({'customerCode': 'KHACHHANG20260001'})
    assert client.put('/api/account/profile', json={field: value}, headers={'X-CSRF-Token': csrf(client)}).status_code == 400
    assert db.customers.find_one({'_id': before['_id']}) == before


def test_explicit_empty_optional_fields_are_unset_and_omitted_fields_retained(app, login_as, csrf):
    client = login_as('CUSTOMER')
    db = app.extensions['mongo_db']
    db.customers.update_one({'customerCode': 'KHACHHANG20260001'}, {'$set': {'phone': '0912345678', 'bio': 'Hello'}})
    assert client.put('/api/account/profile', json={'phone': '', 'address': ''}, headers={'X-CSRF-Token': csrf(client)}).status_code == 200
    row = db.customers.find_one({'customerCode': 'KHACHHANG20260001'})
    assert 'phone' not in row and 'address' not in row and row['bio'] == 'Hello'
    assert client.get('/account').status_code == 200


def test_profile_form_validation_retains_safe_values_and_rejects_duplicate_fields(login_as, csrf):
    from werkzeug.datastructures import MultiDict
    client = login_as('CUSTOMER')
    result = client.post('/account/profile', data={'csrf_token': csrf(client), 'fullName': '<test>', 'phone': 'invalid'})
    assert result.status_code == 400 and 'value="&lt;test&gt;"' in result.text
    assert 'value="invalid"' in result.text
    data = MultiDict([('csrf_token', csrf(client)), ('fullName', 'one'), ('fullName', 'two')])
    assert client.post('/account/profile', data=data).status_code == 400


@pytest.mark.parametrize('kind,suffix', [('JPEG', 'jpg'), ('PNG', 'png'), ('WEBP', 'webp')])
def test_avatar_valid_formats_normalized_private_and_metadata_free(app, login_as, csrf, avatar_directory, kind, suffix):
    client = login_as('CUSTOMER')
    exif = Image.Exif()
    exif[0x010E] = 'private camera metadata'
    result = upload(client, csrf, picture(kind, exif=exif if kind == 'JPEG' else None), f'portrait.{suffix}')
    assert result.status_code == 200
    metadata = app.extensions['mongo_db'].customers.find_one({'customerCode': 'KHACHHANG20260001'})['avatar']
    assert avatar_service.KEY.fullmatch(metadata['key']) and metadata['key'] != f'portrait.{suffix}'
    path = avatar_directory / metadata['key']
    with Image.open(path) as image:
        assert image.format == 'WEBP' and image.size == (512, 384)
        assert not image.getexif() and not image.info.get('exif')
    reply = client.get('/account/avatar')
    assert reply.status_code == 200 and reply.mimetype == 'image/webp'
    assert reply.data == path.read_bytes() and 'no-store' in reply.headers['Cache-Control']
    assert 'private camera metadata' not in str(metadata)
    assert len(list(avatar_directory.iterdir())) == 1


def test_avatar_replace_delete_and_other_customer_ownership(app, login_as, csrf, avatar_directory):
    first = login_as('CUSTOMER')
    second = login_as('CUSTOMER', 'KHACHHANG20260002')
    assert upload(first, csrf).status_code == 200
    old = next(avatar_directory.iterdir())
    assert upload(second, csrf, picture(color='red')).status_code == 200
    own_bytes = first.get('/account/avatar').data
    assert second.get('/account/avatar').data != own_bytes
    assert first.get('/account/avatar?customerCode=KHACHHANG20260002').data == own_bytes
    assert upload(first, csrf, picture(color='blue')).status_code == 200
    assert not old.exists() and len(list(avatar_directory.iterdir())) == 2
    assert first.post('/account/avatar/delete', data={'csrf_token': csrf(first), 'customerCode': 'KHACHHANG20260002'}).status_code == 400
    assert first.post('/account/avatar/delete', data={'csrf_token': csrf(first)}).status_code == 302
    assert first.get('/account/avatar').mimetype == 'image/svg+xml'
    assert second.get('/account/avatar').mimetype == 'image/webp'
    assert len(list(avatar_directory.iterdir())) == 1


@pytest.mark.parametrize('filename,content', [
    ('../../portrait.png', b'fake'), ('C:\\portrait.png', b'fake'), ('portrait.svg', b'<svg/>'),
    ('portrait.exe', b'MZfake'), ('portrait.png', b'<?php fake ?>'), ('portrait.jpg', picture('PNG')),
    ('portrait.png', b'x' * (800 * 1024 + 1)), ('portrait.png', b''),
    ('portrait.png', picture(size=(5000, 4000))),
], ids=['traversal', 'absolute-path', 'svg', 'executable', 'fake-image', 'wrong-format', 'too-large', 'empty', 'pixel-limit'])
def test_invalid_avatar_is_rejected(app, login_as, csrf, avatar_directory, filename, content):
    client = login_as('CUSTOMER')
    assert upload(client, csrf, content, filename).status_code == 400
    assert not avatar_directory.exists() or not list(avatar_directory.iterdir())
    assert 'avatar' not in app.extensions['mongo_db'].customers.find_one({'customerCode': 'KHACHHANG20260001'})


def test_avatar_csrf_auth_permissions_and_storage_traversal(app, login_as, csrf, avatar_directory):
    guest = app.test_client()
    assert guest.get('/account/avatar').status_code == 302
    assert guest.post('/account/avatar').status_code == 302
    admin = login_as('ADMIN')
    # Staff now have their own account profile, but still cannot upload without a file.
    assert admin.get('/account/avatar').status_code == 200
    assert admin.post('/account/avatar', data={'csrf_token': csrf(admin)}).status_code == 400
    customer = login_as('CUSTOMER')
    assert customer.post('/account/avatar', data={'avatar': (BytesIO(picture()), 'a.png')}).status_code == 400
    assert customer.post('/account/avatar/delete').status_code == 400
    with app.app_context():
        for key in ['../outside.webp', '/etc/passwd', '..\\outside.webp', 'wrong.webp', None]:
            with pytest.raises(ValidationError):
                avatar_service.storage_path(key)


def test_avatar_write_and_database_failures_leave_old_image_and_no_temporary_files(app, login_as, csrf, avatar_directory, monkeypatch):
    client = login_as('CUSTOMER')
    assert upload(client, csrf).status_code == 200
    original = next(avatar_directory.iterdir())
    db = app.extensions['mongo_db']
    original_metadata = db.customers.find_one({'customerCode': 'KHACHHANG20260001'})['avatar']
    with monkeypatch.context() as patch:
        patch.setattr(db.customers, 'update_one', lambda *a, **k: (_ for _ in ()).throw(PyMongoError('synthetic failure')))
        assert upload(client, csrf, picture(color='red')).status_code == 503
    assert list(avatar_directory.iterdir()) == [original]
    assert db.customers.find_one({'customerCode': 'KHACHHANG20260001'})['avatar'] == original_metadata
    with monkeypatch.context() as patch:
        patch.setattr(avatar_service.os, 'replace', lambda *a: (_ for _ in ()).throw(OSError('synthetic failure')))
        assert upload(client, csrf).status_code == 400
    assert list(avatar_directory.iterdir()) == [original]
    with app.app_context(), store.user_mutation_lock():
        assert upload(client, csrf).status_code == 409
    assert list(avatar_directory.iterdir()) == [original]


def test_avatar_missing_or_corrupt_reference_falls_back_without_exposing_paths(app, login_as, avatar_directory):
    client = login_as('CUSTOMER')
    app.extensions['mongo_db'].customers.update_one({'customerCode': 'KHACHHANG20260001'}, {'$set': {'avatar': {'key': '../secret'}}})
    assert client.get('/account/avatar').mimetype == 'image/svg+xml'


def test_orphan_cleanup_dry_run_retains_referenced_and_recent_files(app, login_as, csrf, avatar_directory):
    client = login_as('CUSTOMER')
    assert upload(client, csrf).status_code == 200
    referenced = next(avatar_directory.iterdir())
    orphan = avatar_directory / ('a' * 64 + '.webp')
    recent = avatar_directory / ('b' * 64 + '.webp')
    orphan.write_bytes(b'orphan')
    recent.write_bytes(b'recent')
    os.utime(orphan, (1, 1))
    os.utime(referenced, (1, 1))
    runner = app.test_cli_runner()
    assert runner.invoke(args=['cleanup-avatar-orphans']).exit_code == 0
    assert orphan.exists()
    assert runner.invoke(args=['cleanup-avatar-orphans', '--apply']).exit_code == 0
    assert not orphan.exists() and referenced.exists() and recent.exists()


def test_animated_and_decompression_bomb_images_rejected(login_as, csrf, avatar_directory, monkeypatch):
    client = login_as('CUSTOMER')
    content = BytesIO()
    Image.new('RGB', (20, 20), 'red').save(content, 'WEBP', save_all=True,
                                         append_images=[Image.new('RGB', (20, 20), 'blue')], duration=100, loop=0)
    assert upload(client, csrf, content.getvalue(), 'animation.webp').status_code == 400
    normal = picture()
    with monkeypatch.context() as patch:
        patch.setattr(Image, 'MAX_IMAGE_PIXELS', 1)
        assert upload(client, csrf, normal).status_code == 400
    assert not avatar_directory.exists() or not list(avatar_directory.iterdir())


def test_ambiguous_database_commit_never_deletes_the_now_referenced_image(app, login_as, csrf, avatar_directory, monkeypatch):
    client = login_as('CUSTOMER')
    assert upload(client, csrf).status_code == 200
    db = app.extensions['mongo_db']
    original = db.customers.update_one

    def committed_then_disconnected(*args, **kwargs):
        original(*args, **kwargs)
        raise PyMongoError('synthetic post-commit disconnect')

    with monkeypatch.context() as patch:
        patch.setattr(db.customers, 'update_one', committed_then_disconnected)
        assert upload(client, csrf, picture(color='blue')).status_code == 503
    metadata = db.customers.find_one({'customerCode': 'KHACHHANG20260001'})['avatar']
    assert (avatar_directory / metadata['key']).is_file()
    assert client.get('/account/avatar').data == (avatar_directory / metadata['key']).read_bytes()


def test_admin_customer_form_does_not_replace_extended_profile_fields(app, client, login_as, csrf, avatar_directory):
    customer = login_as('CUSTOMER')
    assert upload(customer, csrf).status_code == 200
    db = app.extensions['mongo_db']
    db.customers.update_one({'customerCode': 'KHACHHANG20260001'}, {'$set': {'phone': '0912345678', 'bio': 'Kept'}})
    metadata = db.customers.find_one({'customerCode': 'KHACHHANG20260001'})['avatar']
    reply = client.post('/khach-hang/KHACHHANG20260001/sua', data={
        'csrf_token': csrf(client), 'fullName': 'Updated by staff', 'email': 'business@example.test',
        'address': 'District 7', 'level': 'gold', 'status': 'active', 'joinedAt': '2026-01-10T00:00',
    })
    assert reply.status_code == 302
    row = db.customers.find_one({'customerCode': 'KHACHHANG20260001'})
    assert row['avatar'] == metadata and row['phone'] == '0912345678' and row['bio'] == 'Kept'
