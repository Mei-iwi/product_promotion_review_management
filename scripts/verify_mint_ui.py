"""Headless UI checks against synthetic, in-memory data; never opens the real DB.

Requires Playwright and installed Microsoft Edge. Run with the project venv.
Real transactions remain covered by verify_shopping_replica.py.
"""
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import mongomock
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server, WSGIRequestHandler
    from tests.shopping_support import seeded_app

    class QuietHandler(WSGIRequestHandler):
        def log_request(self, *args, **kwargs):
            pass

    # Mongomock cannot reconcile transactions. Skip fixture reconciliation only;
    # checkout stays unavailable and auth/CSRF still run normally.
    from unittest.mock import patch
    with patch('tests.shopping_support.shopping_repository.reconcile'):
        app, admin, customers, password = seeded_app(mongomock.MongoClient(), 'MINT_UI_SYNTHETIC')
    db = app.extensions['mongo_db']
    # Use local product photography in this isolated fixture only.
    for code, image in [('P1', 'SANPHAM2026110017'), ('P2', 'SANPHAM2026110041')]:
        db.products.update_one({'productCode': code}, {'$set': {'image': f'/static/img/products/{image}.webp'}})
    from repositories.security_repository import utcnow
    db.orders.insert_one({'orderCode': 'UI-COMPLETED', 'customerCode': 'C1', 'orderDate': utcnow(),
                          'items': [{'productCode': 'P1', 'productName': 'Tai nghe Sony WH-1000XM5', 'quantity': 1, 'unitPrice': 500000}],
                          'appliedPromotion': {'promoCode': 'DEMO10', 'discountAmount': 40000},
                          'totalAmount': 460000, 'status': 'completed'})
    db.reviews.insert_one({'reviewCode': 'UI-REVIEW', 'productCode': 'P1', 'rating': 5, 'title': 'Trải nghiệm tốt',
                           'content': 'Dữ liệu tổng hợp dành riêng cho kiểm thử giao diện.', 'status': 'approved',
                           'verifiedPurchase': True, 'customer': {'customerCode': 'C1', 'customerName': 'Khách hàng demo C1'},
                           'createdAt': utcnow()})
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    output = ROOT / 'docs/mint-lavender-ui'
    output.mkdir(exist_ok=True)
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            context = browser.new_context()
            page = context.new_page()
            errors = []
            console_errors = []
            page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)
            page.on('pageerror', lambda error: errors.append(str(error)))

            def visit(path, width, label):
                page.goto(base + path, wait_until='networkidle')
                assert page.locator('main').is_visible(), label
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (width, label)
                assert page.locator('header.app-navbar').evaluate("e => getComputedStyle(e).backgroundColor") == 'rgb(255, 255, 255)', 'Bootstrap/CSS failed to load'
                if width in [360, 1440]:
                    page.screenshot(path=str(output / f'{width}-{label}.png'), full_page=True)
                results.append(f'PASS {width}px {label}: no page overflow')

            def login(email):
                page.goto(base + '/login', wait_until='networkidle')
                page.locator('#email').fill(email)
                page.locator('#password').fill(password)
                page.get_by_role('button', name='Đăng nhập', exact=True).click()
                page.wait_for_url(base + '/catalog')

            for width in ([] if '--states-only' in sys.argv else [360, 390, 768, 1024, 1440]):
                page.set_viewport_size({'width': width, 'height': 960})
                context.clear_cookies()
                visit('/catalog', width, 'guest-catalog')
                if width < 1200:
                    page.get_by_role('button', name='Mở menu điều hướng', exact=True).click()
                    page.locator('#menu').wait_for(state='visible')
                    page.get_by_role('button', name='Mở menu điều hướng', exact=True).click()
                visit('/login', width, 'login')
                page.locator('#password').fill('visibility-check')
                page.get_by_role('button', name='Hiện mật khẩu', exact=True).click()
                assert page.locator('#password').get_attribute('type') == 'text'
                page.get_by_role('button', name='Ẩn mật khẩu', exact=True).click()
                assert page.locator('#password').get_attribute('type') == 'password'
                login(customers[0]['email'])
                visit('/catalog/P1', width, 'product')
                page.get_by_role('button', name='Thêm vào giỏ', exact=True).click()
                page.wait_for_url(base + '/cart')
                visit('/cart', width, 'cart')
                visit('/vouchers', width, 'vouchers')
                visit('/account', width, 'account')
                context.clear_cookies()
                login(admin['email'])
                for path, label in [('/', 'overview'), ('/san-pham', 'products'), ('/san-pham/them', 'product-form'),
                                    ('/khuyen-mai', 'promotions'), ('/khach-hang', 'customers'),
                                    ('/don-hang', 'orders'), ('/danh-gia', 'reviews'),
                                    ('/admin/users', 'users'), ('/bao-cao', 'reports'), ('/thong-ke', 'dashboard')]:
                    visit(path, width, label)
                assert page.locator('.svg-chart-host[aria-busy="true"]').count() == 0
                assert page.locator('#summary .kpi-card').count() == 5
                if width < 1200:
                    page.get_by_role('button', name='Mở menu quản trị', exact=True).click()
                    page.locator('#admin-sidebar.show:not(.showing)').wait_for(state='visible')
                    page.keyboard.press('Escape')
                    page.locator('#admin-sidebar').wait_for(state='hidden')
                else:
                    assert page.locator('#admin-sidebar').is_visible()
                print(f'PASS viewport {width}px navigation, shopping and admin pages', flush=True)

            page.set_viewport_size({'width': 1440, 'height': 960})
            if '--states-only' in sys.argv:
                results.extend(json.loads((output / 'results.json').read_text(encoding='utf-8')))
                login(admin['email'])
            assert not console_errors, console_errors
            page.goto(base + '/catalog?q=DOES-NOT-EXIST', wait_until='networkidle')
            assert page.locator('.empty-state').is_visible()
            assert page.locator('.empty-state a').get_attribute('href') == '/catalog'
            page.goto(base + '/login', wait_until='networkidle')
            page.keyboard.press('Tab')
            assert page.locator('.skip-link').evaluate('e => e === document.activeElement')
            page.keyboard.press('Enter')
            assert page.locator('main').evaluate('e => e === document.activeElement')
            results.append('PASS empty catalog recovery and keyboard skip link')
            # A failed ratings endpoint must not erase the remaining dashboard.
            page.route('**/api/dashboard/ratings', lambda route: route.fulfill(status=503, content_type='application/json', body='{}'))
            visit('/thong-ke', 1440, 'dashboard-partial-error')
            assert page.locator('#ratingDistributionChart [role="alert"]').count() == 1
            assert page.locator('#summary .kpi-card').count() == 5
            assert page.locator('#promotionUsageChart svg').count() == 1
            page.unroute('**/api/dashboard/ratings')
            page.route('**/api/dashboard/ratings', lambda route: route.fulfill(status=200, content_type='application/json', body='{"success":true,"data":{"NC03":[],"NC09":[]}}'))
            visit('/thong-ke', 1440, 'dashboard-no-ratings')
            assert page.locator('#ratingDistributionChart .chart-empty').count() == 1
            assert page.locator('#productRatingChart .chart-empty').count() == 1
            page.unroute('**/api/dashboard/ratings')
            # At 200% desktop zoom, the CSS viewport halves to 720px.
            page.set_viewport_size({'width': 720, 'height': 500})
            visit('/san-pham/them', 720, 'zoom-equivalent-form')
            page.emulate_media(reduced_motion='reduce')
            assert page.locator('.btn-primary').first.evaluate("e => getComputedStyle(e).transitionDuration") == '0s'
            assert not errors, errors
            results.append('PASS JS: no uncaught exceptions; partial API failure isolated; reduced motion respected')
            context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    (output / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'PASS {len(results)} UI checks; screenshots: docs/mint-lavender-ui', flush=True)


if __name__ == '__main__':
    main()
