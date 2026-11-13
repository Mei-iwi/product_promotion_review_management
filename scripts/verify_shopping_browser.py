"""Actual browser flow against an isolated real replica set, no auth/CSRF bypass."""
import os
from pathlib import Path
import re
import sys
import threading
import uuid
from werkzeug.serving import make_server, WSGIRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs): pass


def main():
    from playwright.sync_api import sync_playwright
    from pymongo import MongoClient
    from tests.shopping_support import seeded_app
    uri = os.environ['SHOPPING_TEST_MONGO_URI']
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    app, admin, users, password = seeded_app(client, 'SHOPPING_UI_TEST_' + uuid.uuid4().hex)
    db = app.extensions['mongo_db']
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    output = ROOT / 'docs/shopping-ui'
    output.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            for size, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844)]:
                context = browser.new_context(viewport={'width': width, 'height': height})
                customer = context.new_page()
                staff_context = browser.new_context(viewport={'width': width, 'height': height})
                staff = staff_context.new_page()
                for page, email, landing in [(customer, users[0]['email'], '/catalog'), (staff, admin['email'], '/catalog')]:
                    page.goto(base + '/login', wait_until='networkidle')
                    page.locator('#email').fill(email)
                    page.locator('#password').fill(password)
                    page.get_by_role('button', name='Đăng nhập', exact=True).click()
                    page.wait_for_url(base + landing)
                    page.on('dialog', lambda dialog: dialog.accept())

                def shot(page, label):
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (size, label)
                    page.screenshot(path=str(output / f'{size}-{label}.png'), full_page=True)

                customer.goto(base + '/vouchers', wait_until='networkidle')
                assert 'DEMO10' in customer.locator('main').inner_text()
                shot(customer, 'vouchers')
                customer.goto(base + '/catalog', wait_until='networkidle')
                customer.locator('#search').fill('Sony')
                customer.get_by_role('button', name='Tìm sản phẩm', exact=True).click()
                customer.wait_for_load_state('networkidle')
                assert customer.locator('.shop-product').count() == 1
                shot(customer, 'catalog')
                customer.locator('.shop-product h2 a').click()
                customer.wait_for_load_state('networkidle')
                shot(customer, 'product')
                customer.get_by_role('button', name='Thêm vào giỏ', exact=True).click()
                customer.wait_for_url(base + '/cart')
                customer.locator('#promo-choice').select_option('DEMO10')
                customer.get_by_role('button', name='Áp dụng mã đã chọn', exact=True).click()
                customer.wait_for_load_state('networkidle')
                assert '40.000' in customer.locator('.shop-totals').inner_text()
                shot(customer, 'cart')

                def place(page):
                    page.get_by_role('button', name='Xem lại và thanh toán COD', exact=True).click()
                    page.wait_for_url(re.compile(re.escape(base) + r'/checkout/[A-Za-z0-9_-]+$'))
                    page.locator('#phone').fill('0901234567')
                    if page.locator('#promo-choice option[value="DEMO10"]').count():
                        page.locator('#promo-choice').select_option('')
                        page.get_by_role('button', name='Áp dụng mã', exact=True).click()
                        page.wait_for_load_state('networkidle')
                        assert page.locator('#phone').input_value() == '0901234567'
                        assert page.locator('#promo-choice').input_value() == ''
                        page.locator('#promo-choice').select_option('DEMO10')
                        page.get_by_role('button', name='Áp dụng mã', exact=True).click()
                        page.wait_for_load_state('networkidle')
                        assert page.locator('#phone').input_value() == '0901234567'
                        assert '40.000' in page.locator('.shop-totals').inner_text()
                    shot(page, 'checkout')
                    page.get_by_role('button', name=re.compile('^Đặt hàng')).click()
                    page.wait_for_url(re.compile(r'/confirmation$'))
                    shot(page, 'confirmation')
                    code = page.locator('section.detail-section strong').inner_text()
                    page.get_by_role('link', name='Xem chi tiết đơn', exact=True).click()
                    page.wait_for_url(base + '/account/orders/' + code)
                    return code

                first = place(customer)
                assert db.orders.find_one({'orderCode': first})['status'] == 'pending'
                staff.goto(base + '/don-hang/' + first, wait_until='networkidle')
                staff.locator('button[name="status"][value="confirmed"]').click()
                staff.wait_for_load_state('networkidle')
                assert db.orders.find_one({'orderCode': first})['status'] == 'confirmed'
                customer.reload(wait_until='networkidle')
                shot(customer, 'confirmed-order')
                customer.get_by_role('link', name='Đánh giá sản phẩm', exact=True).click()
                customer.wait_for_load_state('networkidle')
                form = customer.locator('form[data-product-review]').first
                assert form.locator('input[name="productCode"]').input_value() == 'P1'
                form.locator('select[name="rating"]').select_option('5')
                form.locator('input[name="title"]').fill('Trải nghiệm tốt')
                form.locator('textarea[name="content"]').fill('Sản phẩm dùng tốt, giao hàng đầy đủ.')
                customer.get_by_role('button', name='Gửi đánh giá', exact=True).click()
                customer.wait_for_load_state('networkidle')
                review = db.reviews.find_one({'productCode': 'P1', 'orderCode': first})
                assert review['verifiedPurchase'] is True and review['status'] == 'pending'
                assert review['orderCode'] == first
                customer.goto(base + '/account/reviews', wait_until='networkidle')
                assert customer.locator('form[data-product-review]').count() == 0
                assert customer.locator('textarea[name="content"]').count() == 0
                assert 'Tai nghe Sony WH-1000XM5' in customer.locator('main').inner_text()
                shot(customer, 'review')
                staff.goto(base + '/don-hang/' + first, wait_until='networkidle')
                staff.locator('button[name="status"][value="completed"]').click()
                staff.wait_for_load_state('networkidle')
                assert db.orders.find_one({'orderCode': first})['status'] == 'completed'

                original_stock = db.products.find_one({'productCode': 'P2'})['stock']
                customer.goto(base + '/catalog/P2', wait_until='networkidle')
                customer.get_by_role('button', name='Thêm vào giỏ', exact=True).click()
                customer.wait_for_url(base + '/cart')
                second = place(customer)
                customer.get_by_role('button', name='Hủy đơn hàng', exact=True).click()
                customer.wait_for_load_state('networkidle')
                assert db.orders.find_one({'orderCode': second})['status'] == 'cancelled'
                assert db.products.find_one({'productCode': 'P2'})['stock'] == original_stock
                shot(customer, 'cancelled-order')
                context.close()
                staff_context.close()
                print('PASS: ' + size + ' login/search/cart/promo/COD/order/review/admin complete/customer cancel', flush=True)
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        client.close()


if __name__ == '__main__': main()
