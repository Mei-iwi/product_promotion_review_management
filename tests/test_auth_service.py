from datetime import timedelta
import pytest
from services import auth_service as auth
from services.helpers import ValidationError
from repositories import security_repository as store

PASSWORD = 'forest river lantern mountain'


def test_eight_character_password_account_and_change(app):
    with app.app_context():
        password = 'T8k!r9Vm'
        user = auth.create_user({'email': 'eight@example.test', 'password': password, 'role': 'ADMIN'}, bootstrap=True)
        assert auth.authenticate(user['email'], password, 'eight-char-test')[0]['_id'] == user['_id']
        auth.change_password(user, password, 'P4z@w6Ns')
        assert auth.authenticate(user['email'], 'P4z@w6Ns', 'eight-char-test')[0]['_id'] == user['_id']


@pytest.mark.parametrize('password', ['T8k!r9V', 'x' * 129, '12345678', 'password'])
def test_password_length_bounds_and_common_passwords(password):
    with pytest.raises(ValidationError):
        auth.validate_password(password)


def test_argon_session_login_and_revoke(app):
    with app.app_context():
        user = auth.create_user({'email': 'first@example.test', 'password': PASSWORD, 'role': 'ADMIN'}, bootstrap=True)
        assert user['passwordHash'].startswith('$argon2id$v=19$m=19456,t=2,p=1$')
        assert auth.authenticate(' FIRST@example.test ', PASSWORD, '127.0.0.1')[0]['_id'] == user['_id']
        token, session = auth.issue_session(user)
        assert len(token) >= 43 and session['sessionIdHash'] != token
        assert auth.resolve_session(token)[1]['_id'] == user['_id']
        auth.revoke_session(session)
        assert auth.resolve_session(token) == (None, None)


@pytest.mark.parametrize('field', ['idleExpiresAt', 'absoluteExpiresAt'])
def test_session_expiration(app, field):
    with app.app_context():
        token, session = auth.issue_session()
        app.extensions['mongo_db'].sessions.update_one({'_id': session['_id']}, {'$set': {field: store.utcnow() - timedelta(seconds=1)}})
        assert auth.resolve_session(token) == (None, None)


def test_password_revokes_all_and_bootstrap_once(app):
    with app.app_context():
        user = auth.create_user({'email': 'first@example.test', 'password': PASSWORD, 'role': 'ADMIN'}, bootstrap=True)
        token, _ = auth.issue_session(user)
        auth.change_password(user, PASSWORD, 'another ocean violet staircase')
        assert auth.resolve_session(token) == (None, None)
        with pytest.raises(ValidationError):
            auth.create_user({'email': 'next@example.test', 'password': PASSWORD, 'role': 'ADMIN'}, bootstrap=True)


def test_login_lock_auto_expiry_and_shared_ip_limit(app):
    with app.app_context():
        user = auth.create_user({'email': 'first@example.test', 'password': PASSWORD, 'role': 'ADMIN'}, bootstrap=True)
        for _ in range(5):
            assert auth.authenticate(user['email'], 'wrong', 'one')[1] == 401
        assert auth.authenticate(user['email'], PASSWORD, 'one')[0] is None
        app.extensions['mongo_db'].users.update_one({'_id': user['_id']}, {'$set': {'lockedUntil': store.utcnow() - timedelta(seconds=1)}})
        assert auth.authenticate(user['email'], PASSWORD, 'one')[0]
        for _ in range(20):
            auth.authenticate('unknown@example.test', 'wrong', 'other')
        assert auth.authenticate(user['email'], PASSWORD, 'other')[1] == 429
