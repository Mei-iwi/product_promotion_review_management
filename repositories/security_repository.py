"""Security storage. No business data is seeded, deleted or migrated here."""
from contextlib import contextmanager
from datetime import datetime, timedelta
import secrets
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from db.mongo import get_db


def utcnow():
    return datetime.now(__import__('datetime').timezone.utc).replace(tzinfo=None)


def ensure_indexes():
    db = get_db()
    def index(collection, keys, **options):
        # Verify existing definitions before reusing them (also avoids Mongomock's
        # erroneous duplicate scan when rebuilding an existing partial index).
        expected_keys = [(keys, 1)] if isinstance(keys, str) else keys
        actual = collection.index_information().get(options['name'])
        if actual:
            if actual['key'] != expected_keys or any(actual.get(k) != v for k, v in options.items() if k != 'name'):
                raise RuntimeError('Security index không đúng cấu hình: ' + options['name'])
            return
        collection.create_index(keys, **options)
    index(db.users, "emailNormalized", unique=True, name="security_email")
    index(db.users, "customerCode", unique=True, name="security_customer_link",
                          partialFilterExpression={"role": "CUSTOMER", "customerCode": {"$type": "string"}})
    index(db.sessions, "sessionIdHash", unique=True, name="security_session_token")
    index(db.sessions, "userId", name="security_session_user")
    index(db.sessions, "absoluteExpiresAt", expireAfterSeconds=0, name="security_session_ttl")
    index(db.security_limits, "expiresAt", expireAfterSeconds=0, name="security_limit_ttl")
    index(db.audit_logs, [("timestamp", -1)], name="security_audit_time")
    index(db.audit_logs, [("actorUserId", 1), ("timestamp", -1)], name="security_audit_actor")


def revoke_user(user_id):
    get_db().sessions.update_many({"userId": user_id, "revokedAt": None}, {"$set": {"revokedAt": utcnow()}})


def reserve_attempt(key, maximum):
    """Atomic reservation in a 15 minute window, independent of TTL cleanup."""
    limits, now = get_db().security_limits, utcnow()
    try:
        limits.insert_one({"_id": key, "count": 0, "expiresAt": now + timedelta(minutes=15)})
    except DuplicateKeyError:
        pass
    limits.update_one({"_id": key, "expiresAt": {"$lte": now}},
                      {"$set": {"count": 0, "expiresAt": now + timedelta(minutes=15)}})
    return limits.find_one_and_update({"_id": key, "count": {"$lt": maximum}},
                                      {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER)


@contextmanager
def user_mutation_lock():
    """No lease: a dead owner blocks writes instead of permitting split-brain.

    Only an operator who has stopped ALL app/CLI writers may remove a stale lock.
    All account membership/status/password mutations use this lock.
    """
    owner = secrets.token_hex(32)
    try:
        get_db().security_locks.insert_one({"_id": "user-mutations", "owner": owner, "createdAt": utcnow()})
    except DuplicateKeyError as exc:
        raise BlockingIOError("Đang có thao tác tài khoản khác; vui lòng thử lại") from exc
    try:
        yield
    finally:
        get_db().security_locks.delete_one({"_id": "user-mutations", "owner": owner})
