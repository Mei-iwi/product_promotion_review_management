"""Exercise real HTTP/auth/CSRF in Edge, using only an in-memory test database."""
from io import BytesIO
import json
from pathlib import Path
import re
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

    class QuietHandler(WSGIRequestHandler):
        def log_request(self, *args, **kwargs):
            pass

    fixture = app_fixture.__wrapped__()
    app = next(fixture)
    db = app.extensions['mongo_db']
    password = 'orchid prism ' + secrets.token_urlsafe(24)
    new_password = 'ocean glass ' + secrets.token_urlsafe(24)
    with app.app_context():
        admin = auth_service.create_user({'email': 'owner@example.test', 'password': password, 'role': 'ADMIN'}, bootstrap=True)
        user = auth_service.create_user({'email': 'profile@example.test', 'password': password,
                                         'role': 'CUSTOMER', 'customerCode': 'KHACHHANG20260001'}, admin)
    output = ROOT / 'docs/profile-ui'
    output.mkdir(exist_ok=True)
    (ROOT / '.test-tmp').mkdir(exist_ok=True)
    evidence = []
    with tempfile.TemporaryDirectory(prefix='profile-ui-', dir=ROOT / '.test-tmp') as directory:
        app.config['AVATAR_STORAGE_DIR'] = directory
        server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel='msedge', headless=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                other_context = browser.new_context()
                page = context.new_page()
                other = other_context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('dialog', lambda dialog: dialog.accept())

                def login(tab, email, secret):
                    tab.goto(base + '/login', wait_until='networkidle')
                    tab.locator('#email').fill(email)
                    tab.locator('#password').fill(secret)
                    tab.get_by_role('button', name='Đăng nhập', exact=True).click()
                    tab.wait_for_url(base + '/catalog')

                login(page, user['email'], password)
                login(other, user['email'], password)
                page.goto(base + '/account', wait_until='networkidle')
                assert user['customerCode'] not in page.content()
                assert page.locator('#profile-email').input_value() == user['email']
                assert page.locator('form form').count() == 0
                page.locator('#name').fill('Bản nháp đang nhập')
                with page.expect_file_chooser() as chooser:
                    page.get_by_role('button', name='Thay ảnh đại diện', exact=True).click()
                chooser.value.set_files({'name': 'invalid.png', 'mimeType': 'image/png', 'buffer': b'not an image'})
                expect(page.locator('#avatar-upload [data-form-status]')).to_be_visible()
                assert page.locator('#name').input_value() == 'Bản nháp đang nhập'
                image = BytesIO()
                Image.new('RGB', (800, 600), '#14B8A6').save(image, 'PNG')
                page.locator('#avatar-file').set_input_files({'name': 'portrait.png', 'mimeType': 'image/png', 'buffer': image.getvalue()})
                expect(page.locator('#avatar-save')).to_be_enabled()
                assert page.locator('#profile-avatar').get_attribute('src').startswith('data:')
                assert 'avatar' not in db.customers.find_one({'customerCode': user['customerCode']})
                page.locator('#avatar-save').click()
                expect(page.locator('#avatar-upload [data-form-status]')).to_contain_text('Đã cập nhật')
                assert page.locator('#name').input_value() == 'Bản nháp đang nhập'
                assert db.customers.find_one({'customerCode': user['customerCode']})['avatar']['width'] == 512
                evidence.append('PASS avatar preview requires confirmation; upload preserves profile draft')

                values = {'#name': 'Nguyễn Minh Anh', '#profile-phone': '+84912345678', '#profile-birth': '2000-02-29',
                          '#address': '12 Đường Mint, TP.HCM', '#profile-bio': 'Yêu những điều giản dị.'}
                for selector, value in values.items():
                    page.locator(selector).fill(value)
                page.locator('#profile-gender').select_option('undisclosed')
                page.get_by_role('button', name='Lưu thay đổi', exact=True).click()
                expect(page.locator('#profile-form [data-form-status]')).to_contain_text('Đã lưu')
                page.reload(wait_until='networkidle')
                for selector, value in values.items():
                    assert page.locator(selector).input_value() == value
                for width in [360, 390, 768, 1024, 1440]:
                    page.set_viewport_size({'width': width, 'height': 1000})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), width
                    assert page.locator('#avatar-pick').is_visible()
                    assert page.locator('#confirm').is_visible()
                    page.evaluate('window.scrollTo(0, 0)')
                    assert page.locator('header.app-navbar').bounding_box()['y'] == 0
                    page.screenshot(path=str(output / f'{width}-account.png'), full_page=True)
                    evidence.append(f'PASS {width}px profile/forms without page overflow')
                page.locator('#name').fill('Bản nháp cần giữ')
                page.locator('#current').fill('wrong current secret')
                page.locator('#new').fill(new_password)
                page.locator('#confirm').fill(new_password + ' mismatch')
                assert not page.locator('#confirm').evaluate('e => e.checkValidity()')
                page.locator('#confirm').fill(new_password)
                page.get_by_role('button', name='Hiện mật khẩu mới', exact=True).click()
                assert page.locator('#new').get_attribute('type') == 'text'
                page.get_by_role('button', name='Ẩn mật khẩu mới', exact=True).click()
                page.get_by_role('button', name='Cập nhật mật khẩu', exact=True).click()
                expect(page.locator('#password-form [data-form-status]')).to_contain_text('Mật khẩu hiện tại không đúng')
                assert page.locator('#name').input_value() == 'Bản nháp cần giữ'
                assert page.locator('#current').input_value() == ''
                assert page.locator('#new').input_value() == ''
                assert page.locator('#confirm').input_value() == ''
                page.get_by_role('button', name='Xóa ảnh', exact=True).click()
                expect(page.locator('#avatar-delete')).to_be_hidden()
                assert page.locator('#name').input_value() == 'Bản nháp cần giữ'
                assert 'avatar' not in db.customers.find_one({'customerCode': user['customerCode']})
                page.get_by_role('button', name='Hủy chỉnh sửa', exact=True).click()
                assert page.locator('#name').input_value() == 'Nguyễn Minh Anh'
                evidence.append('PASS profile reload/reset, password validation/visibility, independent error drafts and avatar deletion')
                page.locator('#current').fill(password)
                page.locator('#new').fill(new_password)
                page.locator('#confirm').fill(new_password)
                page.get_by_role('button', name='Cập nhật mật khẩu', exact=True).click()
                page.wait_for_url(base + '/login')
                assert 'Đã đổi mật khẩu thành công' in page.locator('main').inner_text()
                assert other_context.request.get(base + '/api/account/profile').status == 401
                login(page, user['email'], new_password)
                page.goto(base + '/account', wait_until='networkidle')
                assert page.locator('#profile-phone').input_value() == '+84912345678'
                evidence.append('PASS password success signs out both sessions; new password login works')
                assert not errors, errors
                context.close()
                other_context.close()
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            fixture.close()
    (output / 'results.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'PASS: {len(evidence)} profile UI scenarios; docs/profile-ui', flush=True)


if __name__ == '__main__':
    main()
