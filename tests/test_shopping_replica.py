from concurrent.futures import ThreadPoolExecutor
import os
import uuid
from datetime import timedelta
from copy import deepcopy
import pytest
from pymongo import MongoClient
from pymongo.collection import Collection
from services import cart_service, checkout_service, order_service, review_service
from services.shopping_common import ShoppingError
from repositories import shopping_repository as repo, report_repository
from repositories.security_repository import utcnow
from tests.shopping_support import seeded_app

pytestmark = pytest.mark.skipif(not os.getenv('SHOPPING_TEST_MONGO_URI'), reason='Run scripts/verify_shopping_replica.py for a real isolated replica set')
RECIPIENT = {'fullName': 'Khách hàng demo', 'address': '12 Đường Demo, Quận 1', 'phone': '0901234567'}


@pytest.fixture()
def shop():
    client = MongoClient(os.environ['SHOPPING_TEST_MONGO_URI'], serverSelectionTimeoutMS=5000)
    app, admin, customers, password = seeded_app(client, 'SHOPPING_TEST_' + uuid.uuid4().hex)
    with app.app_context():
        yield app, admin, customers, app.extensions['mongo_db']
    client.close()


def ready(user, product='P1', promo=True):
    cart_service.change(user, 'add', product, 1)
    if promo:
        cart_service.change(user, 'apply', promo_code='DEMO10')
    return checkout_service.create_quote(user)['_id']


def concurrently(app, callbacks):
    def run(fn):
        with app.app_context():
            try: return fn()
            except ShoppingError as error: return error
    with ThreadPoolExecutor(max_workers=len(callbacks)) as pool:
        return list(pool.map(run, callbacks))


def test_replica_last_product_and_exact_replay(shop):
    app, _, users, db = shop
    db.products.update_one({'productCode': 'P1'}, {'$set': {'stock': 1}})
    keys = [ready(u, promo=False) for u in users]
    results = concurrently(app, [lambda i=i: checkout_service.place_order(users[i], keys[i], RECIPIENT) for i in [0, 1]])
    assert sum(isinstance(r, ShoppingError) for r in results) == 1
    winner = next(i for i, r in enumerate(results) if isinstance(r, dict))
    assert db.orders.count_documents({}) == 1 and db.products.find_one({'productCode': 'P1'})['stock'] == 0
    assert checkout_service.place_order(users[winner], keys[winner], RECIPIENT)['orderCode'] == results[winner]['orderCode']
    assert db.orders.count_documents({}) == 1
    assert repo.cart(users[1-winner])['items'] and not repo.cart(users[winner])['items']


def test_replica_last_promotion_use(shop):
    app, _, users, db = shop
    db.promotions.update_one({'promoCode': 'DEMO10'}, {'$set': {'usageLimit': 1, 'targets': {'productCodes': [], 'categories': []}}})
    keys = [ready(user, product) for user, product in zip(users, ['P1', 'P2'])]
    result = concurrently(app, [lambda i=i: checkout_service.place_order(users[i], keys[i], RECIPIENT) for i in [0, 1]])
    assert sum(isinstance(r, dict) for r in result) == 1
    assert db.orders.count_documents({}) == 1
    assert db.promotions.find_one({'promoCode': 'DEMO10'})['commerceUsed'] == 1
    assert sum(p['stock'] for p in db.products.find({})) == 19


def test_replica_concurrent_duplicate_key_and_conflicting_payload(shop):
    app, _, users, db = shop
    key = ready(users[0])
    results = concurrently(app, [lambda: checkout_service.place_order(users[0], key, RECIPIENT) for _ in range(2)])
    assert all(isinstance(r, dict) for r in results)
    assert results[0]['orderCode'] == results[1]['orderCode'] and db.orders.count_documents({}) == 1
    assert db.products.find_one({'productCode': 'P1'})['stock'] == 9
    assert db.promotions.find_one({'promoCode': 'DEMO10'})['commerceUsed'] == 1
    with pytest.raises(ShoppingError) as error:
        checkout_service.place_order(users[0], key, {**RECIPIENT, 'phone': '0909999999'})
    assert error.value.code == 'idempotency_conflict'
    cart_service.change(users[0], 'add', 'P2', 1)
    checkout_service.place_order(users[0], key, RECIPIENT)
    assert repo.cart(users[0])['items'] == [{'productCode': 'P2', 'quantity': 1}]


def test_replica_cancel_versus_confirm_and_terminal_states(shop):
    app, admin, users, db = shop
    row = checkout_service.place_order(users[0], ready(users[0]), RECIPIENT)
    results = concurrently(app, [lambda: order_service.transition(users[0], row['orderCode'], 'cancelled', own=True),
                                 lambda: order_service.transition(admin, row['orderCode'], 'confirmed')])
    assert sum(isinstance(r, dict) for r in results) == 1
    order = db.orders.find_one({'orderCode': row['orderCode']})
    cancelled = order['status'] == 'cancelled'
    assert db.products.find_one({'productCode': 'P1'})['stock'] == (10 if cancelled else 9)
    assert db.promotions.find_one({'promoCode': 'DEMO10'})['commerceUsed'] == (0 if cancelled else 1)
    assert len(order['statusHistory']) == 2
    if cancelled:
        order_service.transition(users[0], row['orderCode'], 'cancelled', own=True)
        assert db.products.find_one({'productCode': 'P1'})['stock'] == 10
        assert len(db.orders.find_one({'orderCode': row['orderCode']})['statusHistory']) == 2
    else:
        order_service.transition(admin, row['orderCode'], 'completed')
        assert report_repository.nc05()[0]['quantitySold'] == 1
    with pytest.raises(ShoppingError):
        order_service.transition(admin, row['orderCode'], 'confirmed' if cancelled else 'cancelled')


@pytest.mark.parametrize('point', ['orders', 'carts'])
def test_replica_failure_rolls_back_every_collection(shop, monkeypatch, point):
    _, _, users, db = shop
    key = ready(users[0])
    method = 'insert_one' if point == 'orders' else 'update_one'
    original = getattr(Collection, method)
    def fail(self, *args, **kwargs):
        if self.name == point and kwargs.get('session') is not None:
            raise RuntimeError('Injected failure after stock/promotion changes')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Collection, method, fail)
    with pytest.raises(RuntimeError): checkout_service.place_order(users[0], key, RECIPIENT)
    assert db.orders.count_documents({}) == 0
    assert db.products.find_one({'productCode': 'P1'})['stock'] == 10
    assert db.promotions.find_one({'promoCode': 'DEMO10'})['commerceUsed'] == 0
    assert repo.cart(users[0])['items'][0]['quantity'] == 1
    assert db.audit_logs.count_documents({'action': 'orders.create'}) == 0


@pytest.mark.parametrize('collection,changes', [('products', {'price': 550000}), ('products', {'stock': 9}),
                                               ('promotions', {'value': 15})])
def test_replica_changed_quote_requires_new_confirmation(shop, collection, changes):
    _, _, users, db = shop
    key = ready(users[0])
    query = {'productCode': 'P1'} if collection == 'products' else {'promoCode': 'DEMO10'}
    db[collection].update_one(query, {'$set': changes})
    with pytest.raises(ShoppingError) as error: checkout_service.place_order(users[0], key, RECIPIENT)
    assert error.value.code == 'quote_changed'
    assert db.orders.count_documents({}) == 0
    assert db.promotions.find_one({'promoCode': 'DEMO10'})['commerceUsed'] == 0
    assert repo.cart(users[0])['items']


def test_replica_legacy_reconciliation_is_rerunnable_and_no_invented_stock(shop):
    _, admin, users, db = shop
    db.orders.insert_one({'orderCode': 'OLD', 'customerCode': users[0]['customerCode'], 'status': 'pending',
                          'items': [{'productCode': 'P1', 'quantity': 2, 'productName': 'Legacy', 'unitPrice': 500000}],
                          'totalAmount': 960000, 'appliedPromotion': {'promoCode': 'DEMO10', 'discountAmount': 40000}})
    for _ in range(2):
        assert repo.reconcile()['DEMO10'] == 1
        assert db.products.find_one({'productCode': 'P1'})['stock'] == 10
    order_service.transition(admin, 'OLD', 'cancelled')
    assert db.products.find_one({'productCode': 'P1'})['stock'] == 10
    assert db.promotions.find_one({'promoCode': 'DEMO10'})['commerceUsed'] == 0
    assert repo.reconcile()['DEMO10'] == 0


def test_replica_review_verification_and_snapshot_money(shop):
    _, admin, users, db = shop
    key = ready(users[0])
    row = checkout_service.place_order(users[0], key, RECIPIENT)
    assert row['recipient'] == RECIPIENT and row['paymentMethod'] == 'COD' and row['shippingFee'] == 0
    assert all(isinstance(row[k], int) for k in ['subtotal', 'shippingFee', 'totalAmount'])
    assert row['totalAmount'] == 460000
    assert report_repository.nc05() == []  # Pending orders are not reported as sales.
    order_service.transition(admin, row['orderCode'], 'confirmed')
    review = review_service.create_own(users[0], {'productCode': 'P1', 'rating': 5, 'title': 'Hài lòng', 'content': 'Dùng tốt'})
    assert review['verifiedPurchase'] is True and review['status'] == 'pending'
    db.products.update_one({'productCode': 'P1'}, {'$set': {'price': 999999}})
    saved = db.orders.find_one({'orderCode': row['orderCode']})
    assert saved['items'][0]['unitPrice'] == 500000 and saved['totalAmount'] == 460000


def test_replica_quote_ownership_expiry_and_reconciliation_gate(shop):
    _, _, users, db = shop
    key = ready(users[0])
    from werkzeug.exceptions import NotFound
    with pytest.raises(NotFound): checkout_service.place_order(users[1], key, RECIPIENT)
    db.checkout_quotes.update_one({'_id': key}, {'$set': {'expiresAt': utcnow() - timedelta(seconds=1)}})
    with pytest.raises((ShoppingError, NotFound)) as error:
        checkout_service.place_order(users[0], key, RECIPIENT)
    if isinstance(error.value, ShoppingError): assert error.value.code == 'quote_expired'
    db.shopping_state.update_one({'_id': repo.STATE_KEY}, {'$set': {'ready': False}})
    with pytest.raises(ShoppingError) as error: checkout_service.create_quote(users[0])
    assert error.value.code == 'checkout_unavailable'
    assert db.orders.count_documents({}) == 0
    assert db.products.find_one({'productCode': 'P1'})['stock'] == 10
    assert db.promotions.find_one({'promoCode': 'DEMO10'})['commerceUsed'] == 0
