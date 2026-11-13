import click
import re
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from bson.errors import InvalidId
from db.mongo import get_db
from repositories import security_repository as store
from repositories import user_repository
from services import auth_service as auth
from services.access_policy import ROLE_PERMISSIONS, USER_STATUS_LABELS, has_permission
from services.helpers import ValidationError, whitelist


def public_user(user):
    result = {key: (str(user['_id']) if key == 'id' else user.get(key)) for key in
              ('id', 'email', 'role', 'status', 'customerCode', 'createdAt', 'updatedAt', 'lastLoginAt', 'lockedUntil')}
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=7)))
    return result


def get_user(user_id):
    try:
        return get_db().users.find_one({'_id': ObjectId(user_id)})
    except (InvalidId, TypeError):
        return None


def require_action(actor, permission):
    from werkzeug.exceptions import Forbidden
    if not has_permission(actor, permission):
        raise Forbidden()


def account_scope(actor, permission='users.read'):
    require_action(actor, permission)
    if has_permission(actor, 'users.manage_all'):
        return {}
    if has_permission(actor, 'users.manage_customers'):
        return {'role': 'CUSTOMER'}
    from werkzeug.exceptions import Forbidden
    raise Forbidden()


def current_actor(actor, permission):
    fresh = get_db().users.find_one({'_id': (actor or {}).get('_id')})
    if not auth.usable_user(fresh) or fresh['authVersion'] != actor.get('authVersion'):
        from werkzeug.exceptions import Forbidden
        raise Forbidden()
    # usable_user may have auto-unlocked the account in MongoDB.
    fresh = get_db().users.find_one({'_id': fresh['_id']})
    account_scope(fresh, permission)
    return fresh


def managed_user(actor, user_id, permission='users.update'):
    scope = account_scope(actor, permission)
    try:
        target = user_repository.find_scoped(ObjectId(user_id), scope)
    except (InvalidId, TypeError):
        target = None
    if not target:
        from werkzeug.exceptions import NotFound
        raise NotFound()
    return target


def list_users(actor, filters=None, paginate=False):
    query = account_scope(actor)
    filters = filters if filters is not None else {}
    allowed = {'q', 'role', 'status', 'page', 'per_page'}
    if not hasattr(filters, 'items') or set(filters) - allowed:
        raise ValidationError('Bộ lọc tài khoản không hợp lệ')
    if hasattr(filters, 'getlist') and any(len(filters.getlist(k)) != 1 for k in filters):
        raise ValidationError('Không được lặp lại tham số bộ lọc')
    for value in filters.values():
        if not isinstance(value, str):
            raise ValidationError('Giá trị bộ lọc phải là chuỗi')
    if len(filters.get('q', '')) > 254:
        raise ValidationError('Email tìm kiếm tối đa 254 ký tự')
    q = filters.get('q', '').strip()
    role, status = filters.get('role', ''), filters.get('status', '')
    if len(q) > 254 or (role and role not in ROLE_PERMISSIONS) or (status and status not in USER_STATUS_LABELS):
        raise ValidationError('Email, vai trò hoặc trạng thái lọc không hợp lệ')
    if role:
        if query.get('role') and role != query['role']:
            from werkzeug.exceptions import Forbidden
            raise Forbidden()
        query['role'] = role
    if q:
        query['emailNormalized'] = {'$regex': re.escape(q.casefold())}
    if status:
        query['status'] = status

    def integer(key, default, maximum):
        value = filters.get(key, str(default))
        if not re.fullmatch(r'[0-9]{1,6}', value) or not 1 <= int(value) <= maximum:
            raise ValidationError('Trang hoặc số tài khoản mỗi trang không hợp lệ')
        return int(value)

    page = integer('page', 1, 100000)
    per_page = integer('per_page', 10, 100)
    paged = paginate or 'page' in filters or 'per_page' in filters
    rows, total = user_repository.list_users(query, page if paged else None, per_page)
    return {'rows': [public_user(row) for row in rows], 'total': total, 'page': page,
            'per_page': per_page, 'pages': max(1, (total + per_page - 1) // per_page),
            'paged': paged, 'filters': {'q': q, 'role': role, 'status': status, 'per_page': per_page}}


def form_values(data, actor):
    """Only retain bounded, display-safe non-secret form fields after errors."""
    values = {}
    for field in ['email', 'customerCode']:
        value = data.get(field)
        if isinstance(value, str) and len(value) <= (254 if field == 'email' else 100):
            values[field] = value
    if has_permission(actor, 'users.assign_role') and isinstance(data.get('role'), str) and data['role'] in ROLE_PERMISSIONS:
        values['role'] = data['role']
    if isinstance(data.get('status'), str) and data['status'] in USER_STATUS_LABELS:
        values['status'] = data['status']
    return values


def update_user(actor, user_id, data):
    whitelist(data, ['role', 'status', 'password', 'actorPassword', 'customerCode'])
    if set(data) - {'role', 'status', 'password', 'actorPassword', 'customerCode'}:
        raise ValidationError('Trường tài khoản không được phép')
    with store.user_mutation_lock():
        fresh = current_actor(actor, 'users.update')
        target = managed_user(fresh, user_id)
        if not has_permission(fresh, 'users.manage_all'):
            if {'role', 'customerCode'} & set(data) or data.get('status') == 'locked':
                from werkzeug.exceptions import Forbidden
                raise Forbidden()
        role = data.get('role', target['role'])
        status = data.get('status', target['status'])
        if not isinstance(role, str) or role not in ROLE_PERMISSIONS or status not in {'active', 'disabled', 'locked'}:
            raise ValidationError('Role hoặc trạng thái không hợp lệ')
        if role != target['role']:
            require_action(fresh, 'users.assign_role')
        if status != target['status']:
            require_action(fresh, 'users.disable')
        if data.get('password'):
            require_action(fresh, 'users.reset_password')
        changed_security = role != target['role'] or status != target['status'] or bool(data.get('password'))
        privileged_change = role in {'ADMIN', 'ACCOUNT_MANAGER'} or target['role'] in {'ADMIN', 'ACCOUNT_MANAGER'} or (changed_security and (role != 'CUSTOMER' or target['role'] != 'CUSTOMER'))
        if privileged_change and not auth.verify(fresh['passwordHash'], data.get('actorPassword')):
            raise ValidationError('Cần xác thực lại mật khẩu người thực hiện')
        if target['role'] == 'ADMIN' and target['status'] == 'active' and (role != 'ADMIN' or status != 'active'):
            if get_db().users.count_documents({'role': 'ADMIN', 'status': 'active'}) <= 1:
                raise ValidationError('Không thể thay đổi ADMIN hoạt động cuối cùng')
        updates = {'role': role, 'status': status, 'updatedAt': store.utcnow()}
        if 'status' in data:
            updates.update(failedLoginCount=0, lockedUntil=(store.utcnow() + timedelta(minutes=15) if status == 'locked' else None))
        if role == 'CUSTOMER':
            code = data.get('customerCode', target.get('customerCode'))
            if not isinstance(code, str) or not get_db().customers.find_one({'customerCode': code}):
                raise ValidationError('Cần liên kết khách hàng đang hoạt động')
            if (role != target['role'] or code != target.get('customerCode')) and not get_db().customers.find_one({'customerCode': code, 'status': 'active'}):
                raise ValidationError('Cần liên kết khách hàng đang hoạt động')
            updates['customerCode'] = code
        elif data.get('customerCode'):
            raise ValidationError('Chỉ CUSTOMER được liên kết hồ sơ khách hàng')
        if data.get('password'):
            auth.validate_password(data['password'], target['emailNormalized'])
            updates.update(passwordHash=auth.HASHER.hash(data['password']), passwordChangedAt=store.utcnow())
        mutation = {'$set': updates, '$inc': {'authVersion': 1}}
        if role != 'CUSTOMER':
            mutation['$unset'] = {'customerCode': ''}
        from pymongo.errors import DuplicateKeyError
        try:
            get_db().users.update_one({'_id': target['_id']}, mutation)
        except DuplicateKeyError as exc:
            raise ValidationError('Khách hàng đã liên kết với tài khoản khác') from exc
        store.revoke_user(target['_id'])
        if data.get('status') == 'active':
            get_db().security_limits.delete_one({'_id': 'account:' + auth.digest(target['emailNormalized'])})
        auth.audit('users.update', actor=fresh['_id'], resource_type='users', resource_id=target['_id'],
                   metadata={'oldRole': target['role'], 'role': role, 'oldStatus': target['status'], 'status': status,
                             'oldCustomerCode': target.get('customerCode'), 'customerCode': updates.get('customerCode'),
                             'passwordReset': bool(data.get('password'))})
        return get_user(user_id)


def register_cli(app):
    @app.cli.command('bootstrap-admin')
    @click.option('--email', prompt='Email ADMIN')
    def bootstrap_admin(email):
        """Create the first ADMIN only, without seeded credentials."""
        password = click.prompt('Mật khẩu (8–128 ký tự)', hide_input=True, confirmation_prompt=True)
        try:
            user = auth.create_user({'email': email, 'password': password, 'role': 'ADMIN'}, bootstrap=True)
        except (ValidationError, BlockingIOError) as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo('Đã tạo ADMIN: ' + user['email'])
