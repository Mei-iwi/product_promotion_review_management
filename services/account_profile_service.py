"""Own account profiles for every role; staff data never creates a customer link."""
from werkzeug.exceptions import Forbidden

from db.mongo import get_db
from repositories.security_repository import user_mutation_lock
from services import customer_account_service as customer
from services.access_policy import has_permission
from services.auth_service import usable_user

FIELDS = ('fullName', 'phone', 'dateOfBirth', 'gender', 'address', 'bio')


def current_account(principal, permission='account.read_own_profile'):
    fresh = get_db().users.find_one({'_id': (principal or {}).get('_id')})
    if (not usable_user(fresh) or fresh.get('authVersion') != (principal or {}).get('authVersion')
            or not has_permission(fresh, permission)):
        raise Forbidden()
    return fresh


def personal_data(user):
    value = user.get('profile')
    return value if isinstance(value, dict) else {}


def profile(principal):
    user = current_account(principal)
    if user['role'] == 'CUSTOMER':
        return customer.profile(user)
    data = personal_data(user)
    result = {key: data.get(key, '') for key in FIELDS}
    result['fullName'] = result['fullName'] or user['email'].split('@')[0]
    result.update(email=user['email'], role=user['role'])
    if isinstance(data.get('avatar'), dict):
        result['avatar'] = {key: data['avatar'][key] for key in ('key', 'mediaType', 'width', 'height', 'updatedAt') if key in data['avatar']}
    return result


def update_profile(principal, data):
    clean = customer.validate_profile(data)
    user = current_account(principal, 'account.update_own_profile')
    if user['role'] == 'CUSTOMER':
        return customer.update_profile(user, data)
    with user_mutation_lock():
        user = current_account(principal, 'account.update_own_profile')
        # A role change increments authVersion, so an in-flight request cannot
        # switch storage targets after the principal has been checked.
        changes = {}
        if any(clean.values()):
            changes['$set'] = {'profile.' + key: value for key, value in clean.items() if value}
        if any(not value for value in clean.values()):
            changes['$unset'] = {'profile.' + key: '' for key, value in clean.items() if not value}
        if changes:
            get_db().users.update_one({'_id': user['_id'], 'authVersion': user['authVersion']}, changes)
        return profile(user)


def avatar_target(principal, mutable=False):
    """Collection, scoped selector, metadata container, and exact avatar field.

    Mutations call this under user_mutation_lock. No target comes from a request.
    """
    user = current_account(principal, 'account.update_own_profile' if mutable else 'account.read_own_profile')
    if user['role'] == 'CUSTOMER':
        row = customer.mutable_profile(user) if mutable else customer.profile(user)
        return get_db().customers, {'_id': row['_id'], 'customerCode': row['customerCode']}, row, 'avatar'
    return get_db().users, {'_id': user['_id'], 'authVersion': user['authVersion']}, personal_data(user), 'profile.avatar'
