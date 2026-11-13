from concurrent.futures import ThreadPoolExecutor
import mongomock
import pytest
from pymongo.errors import DuplicateKeyError
from db.mongo import init_mongo
from repositories import security_repository as repo


def test_security_indexes_and_unique_links(app):
    with app.app_context():
        repo.ensure_indexes()
        db = app.extensions['mongo_db']
        db.users.insert_one({'emailNormalized': 'one@example.test', 'role': 'CUSTOMER', 'customerCode': 'C1'})
        with pytest.raises(DuplicateKeyError):
            db.users.insert_one({'emailNormalized': 'two@example.test', 'role': 'CUSTOMER', 'customerCode': 'C1'})
        assert db.sessions.index_information()['security_session_ttl']['expireAfterSeconds'] == 0


def test_atomic_limit_and_lock(app):
    def reserve(_):
        with app.app_context():
            return bool(repo.reserve_attempt('shared-ip', 20))
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(40))) == 20
    with app.app_context():
        with repo.user_mutation_lock():
            with pytest.raises(BlockingIOError):
                with repo.user_mutation_lock():
                    pass
        assert app.extensions['mongo_db'].security_locks.count_documents({}) == 0
