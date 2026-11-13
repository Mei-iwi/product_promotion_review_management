"""Optional UI check: pip install playwright, then run with installed Edge.

Runs the real Flask routes against the existing isolated test fixtures. No
authentication/CSRF bypass and no real MongoDB connection or persistent account.
"""
from pathlib import Path
import secrets
import sys
import threading
from werkzeug.serving import make_server, WSGIRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


def main():
    from playwright.sync_api import sync_playwright
    from tests.conftest import app as seeded_app
    from services import auth_service as auth
    generator = seeded_app.__wrapped__()
    app = next(generator)
    password = 'browser phrase ' + secrets.token_hex(24)
    with app.app_context():
        admin = auth.create_user({'email': 'ui-admin@example.test', 'password': password, 'role': 'ADMIN'}, bootstrap=True)
        auth.create_user({'email': 'ui-customer@example.test', 'password': password, 'role': 'CUSTOMER', 'customerCode': 'KHACHHANG20260001'}, admin)
        auth.create_user({'email': 'ui-manager@example.test', 'password': password, 'role': 'ACCOUNT_MANAGER', 'actorPassword': password}, admin)
    output = ROOT / 'docs' / 'security-ui'
    output.mkdir(exist_ok=True)
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            for label, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844)]:
                context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1)
                page = context.new_page()
                for role, email, landing in [('admin', 'ui-admin@example.test', '/catalog'), ('manager', 'ui-manager@example.test', '/catalog'), ('customer', 'ui-customer@example.test', '/catalog')]:
                    page.goto(base + '/login', wait_until='networkidle')
                    assert page.locator('link[href*="bootstrap"]').evaluate('(link) => !!link.sheet'), 'Bootstrap stylesheet unavailable'
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    if role == 'admin':
                        page.screenshot(path=str(output / f'{label}-login.png'), full_page=True)
                    page.locator('#email').fill(email)
                    page.locator('#password').fill(password)
                    page.locator('button[type="submit"], form button').filter(has_text='Đăng nhập').click()
                    page.wait_for_url(base + landing)
                    paths = ['/admin/users', '/admin/users/create'] if role in {'admin', 'manager'} else ['/account', '/account/orders', '/account/reviews']
                    for index, path in enumerate(paths):
                        page.goto(base + path, wait_until='networkidle')
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (label, path)
                        page.screenshot(path=str(output / f'{label}-{role}-{index}.png'), full_page=True)
                    if role == 'manager':
                        assert page.locator('select[name="role"]').count() == 0
                        page.goto(base + '/admin/users', wait_until='networkidle')
                        assert page.locator('table').inner_text().count('ui-admin@example.test') == 0
                        page.locator('table tbody a').first.click()
                        assert page.locator('input[name="customerCode"]').count() == 0
                        assert page.locator('select[name="role"]').count() == 0
                        assert page.locator('input[name="actorPassword"]').count() == 0
                        confirmations = []
                        def cancel(dialog):
                            confirmations.append(dialog.message)
                            dialog.dismiss()
                        page.on('dialog', cancel)
                        page.select_option('select[name="status"]', 'disabled')
                        page.locator('button[type="submit"]').click()
                        assert len(confirmations) == 1
                        assert page.locator('button[type="submit"]').is_enabled()
                        page.select_option('select[name="status"]', 'active')
                        page.locator('input[name="password"]').fill(password)
                        page.locator('button[type="submit"]').click()
                        assert len(confirmations) == 2
                        page.remove_listener('dialog', cancel)
                        page.reload(wait_until='networkidle')
                        page.screenshot(path=str(output / f'{label}-manager-edit.png'), full_page=True)
                    if width < 1200:
                        page.locator('.navbar-toggler').click()
                        page.locator('#menu.show').wait_for()
                    page.locator('button.dropdown-toggle').click()
                    page.locator('button.dropdown-item').filter(has_text='Đăng xuất').click()
                    page.wait_for_url(base + '/login')
                context.close()
                print(f'PASS: {label} login/admin/manager/customer/forms/confirmation/navigation/logout; no horizontal overflow', flush=True)
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        generator.close()


if __name__ == '__main__':
    main()
