from werkzeug.exceptions import NotFound
from datetime import date, datetime
import re
from db.mongo import get_db
from repositories import customer_repository, order_repository, review_repository
from services.access_policy import authorize_object, has_permission
from services.helpers import ValidationError


def profile(principal):
    row = customer_repository.find_by_code(principal['customerCode'])
    if not authorize_object(principal, 'customers.read_own', row):
        raise NotFound()
    return row


def validate_profile(data):
    fields = {'fullName', 'phone', 'dateOfBirth', 'gender', 'address', 'bio'}
    if not isinstance(data, dict) or set(data) - (fields | {'csrf_token'}):
        raise ValidationError('Trường hồ sơ không được phép')
    if any(not isinstance(value, str) for value in data.values()):
        raise ValidationError('Thông tin hồ sơ phải là văn bản')
    clean = {key: value.strip() for key, value in data.items() if key in fields}
    for field, maximum, label in [('fullName', 200, 'Họ tên'), ('address', 500, 'Địa chỉ'), ('bio', 300, 'Giới thiệu')]:
        if field in clean and (len(clean[field]) > maximum or (field == 'fullName' and not clean[field])):
            raise ValidationError(f'{label} không hợp lệ (tối đa {maximum} ký tự)')
    if clean.get('phone'):
        phone = re.sub(r'[ .()\-]', '', clean['phone'])
        if not re.fullmatch(r'(?:0|\+84)(?:[35789]\d{8}|2\d{9})', phone, flags=re.ASCII):
            raise ValidationError('Số điện thoại Việt Nam không hợp lệ')
        clean['phone'] = phone
    if clean.get('dateOfBirth'):
        from services.shopping_common import VIETNAM
        try:
            value = date.fromisoformat(clean['dateOfBirth'])
            if value.isoformat() != clean['dateOfBirth'] or value > datetime.now(VIETNAM).date():
                raise ValueError()
        except ValueError as error:
            raise ValidationError('Ngày sinh phải hợp lệ và không ở tương lai') from error
    if clean.get('gender', '') not in {'', 'male', 'female', 'other', 'undisclosed'}:
        raise ValidationError('Giới tính không hợp lệ')
    return clean


def update_profile(principal, data):
    clean = validate_profile(data)
    from repositories.security_repository import user_mutation_lock
    with user_mutation_lock():
        row = mutable_profile(principal)
        # Omitted fields stay unchanged. Explicitly empty optional fields are removed.
        changes = {}
        if any(clean.values()):
            changes['$set'] = {key: value for key, value in clean.items() if value}
        if any(not value for value in clean.values()):
            changes['$unset'] = {key: '' for key, value in clean.items() if not value}
        if changes:
            get_db().customers.update_one({'_id': row['_id'], 'customerCode': row['customerCode']}, changes)
        return customer_repository.find_by_code(row['customerCode'])


def mutable_profile(principal):
    """Called under the shared account lock, preventing a concurrent relink/revoke."""
    from services.auth_service import usable_user
    from werkzeug.exceptions import Forbidden
    fresh = get_db().users.find_one({'_id': (principal or {}).get('_id')})
    if (not usable_user(fresh) or fresh.get('authVersion') != principal.get('authVersion')
            or not has_permission(fresh, 'customers.update_own_profile')):
        raise Forbidden()
    row = profile(fresh)
    if not authorize_object(fresh, 'customers.update_own_profile', row):
        raise NotFound()
    return row


def orders(principal, status=''):
    if not isinstance(status, str) or status not in {'', 'pending', 'confirmed', 'completed', 'cancelled'}:
        raise ValidationError('Trạng thái đơn không hợp lệ')
    return order_repository.find_orders({'customerCode': principal['customerCode'], 'status': status})


def order(principal, code):
    # Ownership is part of the database query, including the detail endpoint.
    row = get_db().orders.find_one({'orderCode': code, 'customerCode': principal['customerCode']})
    if not authorize_object(principal, 'orders.read_own', row):
        raise NotFound()
    return row


def reviews(principal):
    return review_repository.find_reviews({'customerCode': principal['customerCode']})


def review_history(principal):
    rows = reviews(principal)
    products = review_repository.reviewed_products({row['productCode'] for row in rows})
    for row in rows:
        product = products.get(row['productCode'])
        row['product'] = {'name': (product or {}).get('name') or row.get('productName') or row['productCode'],
                          'image': (product or {}).get('image') or (product or {}).get('imageUrl') or row.get('productImage'),
                          'available': bool(product and product.get('status') == 'active')}
    return rows
