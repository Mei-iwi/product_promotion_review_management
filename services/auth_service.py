import hashlib
import re
import secrets
from datetime import timedelta
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from pymongo.errors import DuplicateKeyError
from db.mongo import get_db
from repositories import security_repository as store
from services.access_policy import ROLE_PERMISSIONS
from services.helpers import ValidationError, whitelist

HASHER = PasswordHasher(memory_cost=19456, time_cost=2, parallelism=1, type=Type.ID)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))
LOGIN_ERROR = 'Email hoặc mật khẩu không hợp lệ, hoặc tài khoản chưa thể truy cập.'


def digest(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def normalize_email(value):
    if not isinstance(value, str) or len(value) > 254 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', value.strip()):
        raise ValidationError('Email không hợp lệ')
    return value.strip().casefold()


def validate_password(password, email=''):
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise ValidationError('Mật khẩu phải dài từ 8 đến 128 ký tự')
    compact = re.sub(r'[^\w]', '', password.casefold())
    common = {'password', 'password123456789', '12345678', '123456789012345', '12345678901234567890', 'qwerty123', 'qwertyuiopasdfgh', 'admin123', 'letmeinletmein', 'matkhau', 'iloveyou'}
    identity = email.split('@')[0].casefold()
    if len(set(compact)) < 5 or any(word in compact for word in common) or (len(identity) >= 3 and identity in compact):
        raise ValidationError('Mật khẩu quá dễ đoán hoặc chứa thông tin định danh')


def verify(password_hash, password):
    if not isinstance(password, str) or len(password) > 128:
        return False
    try:
        return HASHER.verify(password_hash, password)
    except (VerificationError, InvalidHashError, TypeError):
        return False


def audit(action, result='success', actor=None, resource_type=None, resource_id=None, metadata=None):
    from flask import g, has_request_context, request
    # Metadata is explicitly constructed by callers; never pass a request body.
    get_db().audit_logs.insert_one({
        'actorUserId': actor, 'action': action, 'resourceType': resource_type,
        'resourceId': str(resource_id) if resource_id is not None else None, 'timestamp': store.utcnow(),
        'result': result, 'requestId': getattr(g, 'request_id', None) if has_request_context() else None,
        'ipAddress': request.remote_addr if has_request_context() else None, 'metadata': metadata or {},
    })


def usable_user(user):
    if not user or user.get('role') not in ROLE_PERMISSIONS:
        return False
    now = store.utcnow()
    if user.get('status') == 'locked' and user.get('lockedUntil') and user['lockedUntil'] <= now:
        get_db().users.update_one({'_id': user['_id'], 'status': 'locked', 'lockedUntil': {'$lte': now}},
                                  {'$set': {'status': 'active', 'lockedUntil': None, 'failedLoginCount': 0}})
        user = get_db().users.find_one({'_id': user['_id']})
    if user.get('status') != 'active':
        return False
    if user['role'] == 'CUSTOMER':
        return bool(get_db().customers.find_one({'customerCode': user.get('customerCode'), 'status': 'active'}))
    return True


def create_user(data, actor=None, bootstrap=False):
    whitelist(data, ['email', 'password', 'role', 'customerCode', 'actorPassword'])
    email = normalize_email(data.get('email'))
    validate_password(data.get('password'), email)
    with store.user_mutation_lock():
        from services.user_service import current_actor, require_action
        from services.access_policy import has_permission
        from werkzeug.exceptions import Forbidden
        fresh = None
        if bootstrap:
            role = data.get('role')
            if role != 'ADMIN':
                raise ValidationError('Bootstrap chỉ được tạo ADMIN')
            if get_db().users.count_documents({'role': 'ADMIN'}) > 0:
                raise ValidationError('Đã có ADMIN; bootstrap chỉ được chạy một lần')
        else:
            fresh = current_actor(actor, 'users.create')
            if has_permission(fresh, 'users.manage_all'):
                require_action(fresh, 'users.assign_role')
                role = data.get('role')
            else:
                if data.get('role', 'CUSTOMER') != 'CUSTOMER':
                    raise Forbidden()
                role = 'CUSTOMER'
        if not isinstance(role, str) or role not in ROLE_PERMISSIONS:
            raise ValidationError('Vai trò không hợp lệ')
        if not bootstrap and role in {'ADMIN', 'ACCOUNT_MANAGER'} and not verify(fresh['passwordHash'], data.get('actorPassword')):
            raise ValidationError('Cần xác thực lại mật khẩu người thực hiện')
        doc = {'email': email, 'emailNormalized': email, 'passwordHash': HASHER.hash(data['password']),
               'role': role, 'status': 'active', 'authVersion': 1, 'failedLoginCount': 0, 'lockedUntil': None,
               'createdAt': store.utcnow(), 'updatedAt': store.utcnow(), 'lastLoginAt': None,
               'passwordChangedAt': None}
        if role == 'CUSTOMER':
            code = data.get('customerCode')
            if not isinstance(code, str) or not get_db().customers.find_one({'customerCode': code, 'status': 'active'}):
                raise ValidationError('Cần liên kết khách hàng đang hoạt động')
            doc['customerCode'] = code
        elif data.get('customerCode'):
            raise ValidationError('Chỉ CUSTOMER được liên kết hồ sơ khách hàng')
        try:
            get_db().users.insert_one(doc)
        except DuplicateKeyError as exc:
            raise ValidationError('Email hoặc liên kết khách hàng đã tồn tại') from exc
        audit('users.create', actor=fresh['_id'] if fresh else None, resource_type='users',
              resource_id=doc['_id'], metadata={'role': role, 'status': 'active', 'customerCode': doc.get('customerCode')})
    return doc


def issue_session(user=None):
    now, token = store.utcnow(), secrets.token_urlsafe(32)
    session = {'sessionIdHash': digest(token), 'userId': user['_id'] if user else None,
               'csrfToken': secrets.token_urlsafe(32), 'createdAt': now, 'lastSeenAt': now,
               'idleExpiresAt': now + timedelta(minutes=30), 'absoluteExpiresAt': now + timedelta(hours=8),
               'revokedAt': None, 'authVersionAtIssue': user['authVersion'] if user else None}
    get_db().sessions.insert_one(session)
    return token, session


def resolve_session(token):
    if not isinstance(token, str) or len(token) > 128:
        return None, None
    now = store.utcnow()
    row = get_db().sessions.find_one({'sessionIdHash': digest(token), 'revokedAt': None,
                                     'idleExpiresAt': {'$gt': now}, 'absoluteExpiresAt': {'$gt': now}})
    if not row:
        return None, None
    user = get_db().users.find_one({'_id': row['userId']}) if row['userId'] else None
    if row['userId'] and (not usable_user(user) or user.get('authVersion') != row['authVersionAtIssue']):
        revoke_session(row)
        return None, None
    # Return a fresh principal, including auto-unlock changes, from the trusted store.
    if user:
        user = get_db().users.find_one({'_id': user['_id']})
    get_db().sessions.update_one({'_id': row['_id'], 'revokedAt': None},
                                {'$set': {'lastSeenAt': now, 'idleExpiresAt': min(now + timedelta(minutes=30), row['absoluteExpiresAt'])}})
    return row, user


def revoke_session(row):
    if row:
        get_db().sessions.update_one({'_id': row['_id']}, {'$set': {'revokedAt': store.utcnow()}})


def authenticate(email, password, ip):
    if not store.reserve_attempt('ip:' + digest(ip or 'unknown'), 20):
        audit('login.rate_limit', 'denied')
        return None, 429
    try:
        email = normalize_email(email)
    except ValidationError:
        email = ''
    user = get_db().users.find_one({'emailNormalized': email})
    valid = verify(user['passwordHash'] if user else DUMMY_HASH, password)
    if not valid or not usable_user(user):
        if user and user.get('status') == 'active' and not valid:
            attempt = store.reserve_attempt('account:' + digest(email), 5)
            count = attempt['count'] if attempt else 5
            update = {'failedLoginCount': count}
            if count >= 5:
                update.update(status='locked', lockedUntil=store.utcnow() + timedelta(minutes=15))
            get_db().users.update_one({'_id': user['_id'], 'status': 'active'}, {'$set': update})
            if count >= 5:
                store.revoke_user(user['_id'])
                audit('account.lock', actor=user['_id'])
        audit('login', 'denied', actor=user['_id'] if user else None)
        return None, 401
    updates = {'lastLoginAt': store.utcnow(), 'failedLoginCount': 0}
    if HASHER.check_needs_rehash(user['passwordHash']):
        updates['passwordHash'] = HASHER.hash(password)
    get_db().users.update_one({'_id': user['_id'], 'authVersion': user['authVersion']}, {'$set': updates})
    get_db().security_limits.delete_one({'_id': 'account:' + digest(email)})
    audit('login', actor=user['_id'])
    return get_db().users.find_one({'_id': user['_id']}), 200


def change_password(principal, current, new):
    with store.user_mutation_lock():
        user = get_db().users.find_one({'_id': principal['_id']})
        if not usable_user(user) or user['authVersion'] != principal['authVersion'] or not verify(user['passwordHash'], current):
            raise ValidationError('Mật khẩu hiện tại không đúng')
        validate_password(new, user['emailNormalized'])
        if verify(user['passwordHash'], new):
            raise ValidationError('Mật khẩu mới phải khác mật khẩu hiện tại')
        get_db().users.update_one({'_id': user['_id']}, {'$set': {'passwordHash': HASHER.hash(new), 'passwordChangedAt': store.utcnow()}, '$inc': {'authVersion': 1}})
        store.revoke_user(user['_id'])
        audit('account.change_password', actor=user['_id'])
