"""Voucher usability checks in Edge with isolated, in-memory fixtures only."""
import json
from pathlib import Path
import secrets
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from playwright.sync_api import sync_playwright, expect
    from werkzeug.serving import make_server, WSGIRequestHandler
    from tests.conftest import app as app_fixture
    from tests.test_promotion_offers import offers as offers_fixture
    from services import auth_service, cart_service

    class QuietHandler(WSGIRequestHandler):
        def log_request(self, *args, **kwargs):
            pass

    fixture = app_fixture.__wrapped__()
    app = next(fixture)
    offers_fixture.__wrapped__(app)
    password = 'orchid lantern ' + secrets.token_urlsafe(24)
    with app.app_context():
        admin = auth_service.create_user({'email': 'owner@example.test', 'role': 'ADMIN', 'password': password}, bootstrap=True)
        customer = auth_service.create_user({'email': 'shopper@example.test', 'role': 'CUSTOMER',
                                             'customerCode': 'KHACHHANG20260001', 'password': password}, admin)
        cart_service.change(customer, 'add', 'SANPHAM2026090007', 1)
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    output = ROOT / 'docs/voucher-ui'
    output.mkdir(exist_ok=True)
    evidence = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, permissions=['clipboard-read', 'clipboard-write'])
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + '/login', wait_until='networkidle')
            page.locator('#email').fill(customer['email'])
            page.locator('#password').fill(password)
            page.get_by_role('button', name='Đăng nhập', exact=True).click()
            page.wait_for_url(base + '/catalog')
            page.goto(base + '/vouchers', wait_until='networkidle')
            assert page.locator('.voucher-ticket.is-eligible').count() == 2
            assert 'PRIVATE-SECRET' not in page.content() and 'commerceUsed' not in page.content()
            for width in [360, 390, 768, 1024, 1440]:
                page.set_viewport_size({'width': width, 'height': 1000})
                page.evaluate('window.scrollTo(0,0)')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), width
                page.screenshot(path=str(output / f'{width}-vouchers.png'), full_page=True)
                evidence.append(f'PASS {width}px voucher cards, controls and page without horizontal overflow')
            card = page.locator('.voucher-ticket').filter(has=page.locator('code', has_text='GOOD10'))
            card.get_by_role('button', name='Sao chép mã GOOD10', exact=True).click()
            expect(card.locator('[data-copy-feedback]')).to_contain_text('Đã sao chép mã GOOD10')
            assert page.evaluate('navigator.clipboard.readText()') == 'GOOD10'
            card.locator('summary').click()
            assert card.locator('details').get_attribute('open') is not None
            assert 'AirPods' in card.locator('details').inner_text()
            page.evaluate("() => { navigator.clipboard.writeText = () => Promise.reject(new Error('test denied')); }")
            card.get_by_role('button', name='Sao chép mã GOOD10', exact=True).click()
            expect(card.locator('[data-copy-feedback]')).to_contain_text('Mã đã được chọn')
            assert page.evaluate('getSelection().toString()') == 'GOOD10'
            evidence.append('PASS copy code, clipboard-denied fallback and keyboard-accessible conditions')
            card.get_by_role('button', name='Dùng mã này', exact=True).click()
            page.wait_for_url(base + '/cart')
            assert 'GOOD10' in page.locator('main').inner_text()
            assert app.extensions['mongo_db'].promotions.find_one({'promoCode': 'GOOD10'}).get('commerceUsed', 0) == 0
            evidence.append('PASS voucher applies to own cart without reserving usage')
            assert page.get_by_role('button', name='Cập nhật', exact=True).count() == 0
            with page.expect_navigation(wait_until='networkidle'):
                page.locator('input[name="quantity"]').fill('2')
                page.locator('input[name="quantity"]').press('Tab')
            assert '10.880.000' in page.locator('.shop-totals').inner_text()
            evidence.append('PASS cart reprices quantity without an update button')
            assert not errors, errors
            context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        fixture.close()
    (output / 'results.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'PASS {len(evidence)} voucher UI scenarios; docs/voucher-ui', flush=True)


if __name__ == '__main__':
    main()
