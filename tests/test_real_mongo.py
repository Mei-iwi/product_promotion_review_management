"""Opt-in integration tests; run scripts/verify_security_runtime.py for isolation."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import os
import secrets
import uuid
import pytest
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from app import create_app
from db.mongo import get_db
from repositories import security_repository as store
from services import auth_service as auth, user_service
from services.helpers import ValidationError

pytestmark = pytest.mark.skipif(not os.getenv('SECURITY_TEST_MONGO_URI'), reason='Requires isolated real MongoDB: scripts/verify_security_runtime.py')


@pytest.fixture()
def real_app():
    uri = os.environ['SECURITY_TEST_MONGO_URI']
    # Use the provisioned isolated test database; never drop an arbitrary database.
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    database = os.environ['SECURITY_TEST_MONGO_DB']
    assert database.startswith('RBAC_SECURITY_TEST_')
    app = create_app({'TESTING': True, 'APP_ENV': 'development', 'MONGO_DB': database, 'SECRET_KEY': secrets.token_hex(32)}, client)
    with app.app_context():
        # Dedicated fresh container is enforced by the runtime verifier. Collections
        # use unique identities between tests and are not dropped here.
        yield app
    client.close()


def test_real_unique_partial_index_and_explicit_session_expiry(real_app):
    db = get_db()
    code = uuid.uuid4().hex
    db.customers.insert_one({'customerCode': code, 'status': 'active'})
    db.users.insert_one({'emailNormalized': uuid.uuid4().hex, 'role': 'CUSTOMER', 'customerCode': code})
    with pytest.raises(DuplicateKeyError):
        db.users.insert_one({'emailNormalized': uuid.uuid4().hex, 'role': 'CUSTOMER', 'customerCode': code})
    db.users.insert_one({'emailNormalized': uuid.uuid4().hex, 'role': 'ANALYST'})
    db.users.insert_one({'emailNormalized': uuid.uuid4().hex, 'role': 'ANALYST'})
    token, row = auth.issue_session()
    db.sessions.update_one({'_id': row['_id']}, {'$set': {'idleExpiresAt': store.utcnow() - timedelta(seconds=1)}})
    assert db.sessions.find_one({'_id': row['_id']}) is not None
    assert auth.resolve_session(token) == (None, None)


def test_real_rate_reservations_multiworker(real_app):
    key = 'integration:' + uuid.uuid4().hex
    def attempt(_):
        with real_app.app_context():
            return bool(store.reserve_attempt(key, 20))
    with ThreadPoolExecutor(max_workers=16) as pool:
        assert sum(pool.map(attempt, range(80))) == 20


def test_real_last_admin_concurrency(real_app):
    db = get_db()
    password = 'integration phrase ' + secrets.token_hex(16)
    # Only this test creates ADMIN users in this dedicated container database.
    assert db.users.count_documents({'role': 'ADMIN'}) == 0
    a = auth.create_user({'email': 'first-' + uuid.uuid4().hex + '@example.test', 'password': password, 'role': 'ADMIN'}, bootstrap=True)
    b = auth.create_user({'email': 'second-' + uuid.uuid4().hex + '@example.test', 'password': password, 'role': 'ADMIN', 'actorPassword': password}, a)
    def disable(actor):
        with real_app.app_context():
            try:
                user_service.update_user(actor, str(actor['_id']), {'status': 'disabled', 'actorPassword': password})
                return True
            except (ValidationError, BlockingIOError):
                return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(disable, [a, b])) == 1
    assert db.users.count_documents({'role': 'ADMIN', 'status': 'active'}) == 1
