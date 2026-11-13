"""Verify all staff profiles in Edge using a synthetic in-memory database."""
from io import BytesIO
import json
from pathlib import Path
import secrets
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from PIL import Image
    from playwright.sync_api import sync_playwright, expect
    from werkzeug.serving import make_server, WSGIRequestHandler
    from tests.conftest import app as app_fixture
    from services import auth_service
    from services.access_policy import ROLE_LABELS, ROLE_PERMISSIONS

    class QuietHandler(WSGIRequestHandler):
        def log_request(self, *args, **kwargs):
            pass

    fixture = app_fixture.__wrapped__()
    app = next(fixture)
    db = app.extensions['mongo_db']
    password = 'orchid prism ' + secrets.token_urlsafe(24)
    with app.app_context():
        admin = auth_service.create_user({'email': 'owner@example.test', 'password': password, 'role': 'ADMIN'}, bootstrap=True)
        users = [admin]
        for role in ROLE_PERMISSIONS:
            if role in {'ADMIN', 'CUSTOMER'}:
                continue
            users.append(auth_service.create_user({'email': role.lower() + '@example.test', 'password': password,
                                                   'role': role, **({'actorPassword': password} if role == 'ACCOUNT_MANAGER' else {})}, admin))
    customers_before = list(db.customers.find())
    output = ROOT / 'docs/staff-profile-ui'
    output.mkdir(exist_ok=True)
    (ROOT / '.test-tmp').mkdir(exist_ok=True)
    evidence = []
    with tempfile.TemporaryDirectory(dir=ROOT / '.test-tmp') as directory:
        app.config['AVATAR_STORAGE_DIR'] = directory
        server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel='msedge', headless=True)
                context = browser.new_context()
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                for user in users:
                    page.goto(base + '/login', wait_until='networkidle')
                    page.locator('#email').fill(user['email'])
                    page.locator('#password').fill(password)
                    page.get_by_role('button', name='Đăng nhập', exact=True).click()
                    page.wait_for_url(base + '/catalog')
                    page.goto(base + '/account', wait_until='networkidle')
                    assert page.locator('#profile-level').input_value() == ROLE_LABELS[user['role']]
                    assert page.locator('#profile-email').input_value() == user['email']
                    assert page.locator('#profile-email').get_attribute('readonly') is not None
                    assert page.locator('#password-form').is_visible()
                    page.locator('#name').fill('Hồ sơ ' + ROLE_LABELS[user['role']])
                    page.locator('#profile-phone').fill('0912345678')
                    page.get_by_role('button', name='Lưu thay đổi', exact=True).click()
                    expect(page.locator('#profile-form [data-form-status]')).to_contain_text('Đã lưu')
                    if user['role'] in {'ADMIN', 'ANALYST'}:
                        content = BytesIO()
                        Image.new('RGB', (80, 100), 'teal' if user['role'] == 'ADMIN' else 'purple').save(content, 'PNG')
                        page.locator('#avatar-file').set_input_files({'name': 'portrait.png', 'mimeType': 'image/png', 'buffer': content.getvalue()})
                        expect(page.locator('#avatar-save')).to_be_enabled()
                        page.locator('#avatar-save').click()
                        expect(page.locator('#avatar-upload [data-form-status]')).to_contain_text('Đã cập nhật')
                        assert db.users.find_one({'_id': user['_id']})['profile']['avatar']['key']
                    page.reload(wait_until='networkidle')
                    assert page.locator('#profile-phone').input_value() == '0912345678'
                    for width in [390, 1440]:
                        page.set_viewport_size({'width': width, 'height': 1000})
                        page.evaluate('window.scrollTo(0,0)')
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (user['role'], width)
                        page.screenshot(path=str(output / f'{user["role"].lower()}-{width}.png'), full_page=True)
                    evidence.append(f'PASS {user["role"]}: profile save/reload, own role/email, password form, mobile and desktop')
                assert list(db.customers.find()) == customers_before
                assert not errors, errors
                context.close()
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            fixture.close()
    (output / 'results.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'PASS {len(evidence)} staff roles; docs/staff-profile-ui', flush=True)


if __name__ == '__main__':
    main()
