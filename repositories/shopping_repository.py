"""MongoDB-only operations for carts, quotes, transactions and reconciliation."""
from flask import current_app
from pymongo import ReturnDocument, ReadPreference
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from pymongo.errors import DuplicateKeyError
from db.mongo import get_db
from repositories.security_repository import utcnow

STATE_KEY = 'promotion-usage-v1'


def ensure_indexes():
    db = get_db()
    if 'shopping_quote_ttl' not in db.checkout_quotes.index_information():
        db.checkout_quotes.create_index('expiresAt', expireAfterSeconds=0, name='shopping_quote_ttl')
    if 'shopping_checkout_unique' not in db.orders.index_information():
        db.orders.create_index([('customerCode', 1), ('checkoutKey', 1)], unique=True,
                              partialFilterExpression={'checkoutKey': {'$type': 'string'}}, name='shopping_checkout_unique')
    # Reuse an existing equivalent business index instead of renaming it.
    if not any(info['key'] == [('orderCode', 1)] and info.get('unique') for info in db.orders.index_information().values()):
        db.orders.create_index('orderCode', unique=True, name='shopping_order_code',
                               partialFilterExpression={'orderCode': {'$type': 'string'}})


def transaction_supported():
    try:
        hello = get_db().client.admin.command('hello')
        return bool(hello.get('setName') or hello.get('msg') == 'isdbgrid')
    except (NotImplementedError, AttributeError):
        return False


def transaction(callback):
    with get_db().client.start_session() as session:
        return session.with_transaction(callback, read_concern=ReadConcern('snapshot'),
                                        write_concern=WriteConcern('majority'), read_preference=ReadPreference.PRIMARY,
                                        max_commit_time_ms=10000)


def cart(principal, session=None):
    return get_db().carts.find_one({'_id': principal['_id'], 'customerCode': principal['customerCode']}, session=session) or {
        '_id': principal['_id'], 'userId': principal['_id'], 'customerCode': principal['customerCode'],
        'items': [], 'promoCode': '', 'version': 0}


def save_cart(principal, previous, items, promo_code):
    db = get_db()
    changes = {'items': items, 'promoCode': promo_code, 'updatedAt': utcnow()}
    result = db.carts.update_one({'_id': principal['_id'], 'customerCode': principal['customerCode'], 'version': previous['version']},
                                {'$set': changes, '$inc': {'version': 1}})
    if result.matched_count:
        return True
    if previous['version'] == 0:
        try:
            db.carts.insert_one({**previous, **changes, 'version': 1})
            return True
        except DuplicateKeyError:
            pass
    return False


def products(codes, session=None):
    return {p['productCode']: p for p in get_db().products.find({'productCode': {'$in': codes}}, session=session)}


def promotion(code, session=None):
    return get_db().promotions.find_one({'promoCode': code}, session=session) if code else None


def quote(principal, key, session=None):
    return get_db().checkout_quotes.find_one({'_id': key, 'userId': principal['_id'], 'customerCode': principal['customerCode']}, session=session)


def existing_order(principal, key, session=None):
    return get_db().orders.find_one({'customerCode': principal['customerCode'], 'checkoutKey': key}, session=session)


def fence(session):
    return get_db().shopping_state.find_one_and_update({'_id': STATE_KEY, 'ready': True},
                                                      {'$inc': {'epoch': 1}}, session=session, return_document=ReturnDocument.AFTER)


def reconcile():
    """Rerunnable: derive usage from valid orders, not by adding previous counts.

    All checkout/status callbacks also write the state document, so a concurrent
    transaction conflicts and retries rather than overwriting newer usage.
    Legacy records receive only an explicit usage-accounted marker, never a stock
    reservation marker; cancellation cannot invent an inventory refund.
    """
    def run(session):
        db = get_db()
        db.shopping_state.update_one({'_id': STATE_KEY}, {'$inc': {'epoch': 1}}, upsert=True, session=session)
        promos = list(db.promotions.find({}, session=session))
        counts = {}
        for promo in promos:
            query = {'appliedPromotion.promoCode': promo['promoCode'], 'status': {'$in': ['pending', 'confirmed', 'completed']}}
            used = db.orders.count_documents(query, session=session)
            db.promotions.update_one({'_id': promo['_id']}, {'$set': {'commerceUsed': used}}, session=session)
            db.orders.update_many(query, {'$set': {'promotionUsageAccounted': True}}, session=session)
            counts[promo['promoCode']] = used
        db.orders.update_many({'status': 'cancelled', 'promotionUsageAccounted': True},
                              {'$set': {'promotionUsageAccounted': False}}, session=session)
        db.shopping_state.update_one({'_id': STATE_KEY}, {'$set': {'ready': True, 'reconciledAt': utcnow(), 'schemaVersion': 1}}, session=session)
        return counts
    return transaction(run)
