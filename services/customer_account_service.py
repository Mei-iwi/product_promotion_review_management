from werkzeug.exceptions import NotFound
from db.mongo import get_db
from repositories import customer_repository, order_repository, review_repository
from services.access_policy import authorize_object
from services.helpers import ValidationError


def profile(principal):
    row = customer_repository.find_by_code(principal['customerCode'])
    if not authorize_object(principal, 'customers.read_own', row):
        raise NotFound()
    return row


def update_profile(principal, data):
    if set(data) - {'fullName', 'address', 'csrf_token'}:
        raise ValidationError('Chỉ được cập nhật họ tên và địa chỉ')
    row = profile(principal)
    if not authorize_object(principal, 'customers.update_own_profile', row):
        raise NotFound()
    clean = {key: value.strip() for key, value in data.items() if key in {'fullName', 'address'} and isinstance(value, str)}
    if not clean.get('fullName') or len(clean['fullName']) > 200 or len(clean.get('address', '')) > 500:
        raise ValidationError('Thông tin hồ sơ không hợp lệ')
    return customer_repository.update(row['customerCode'], clean)


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
