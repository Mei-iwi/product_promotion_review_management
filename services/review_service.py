from datetime import datetime
from pymongo.errors import DuplicateKeyError
from db.mongo import get_db
from repositories import review_repository as repo
from repositories.customer_repository import find_by_code as find_customer
from repositories.product_repository import find_by_code as find_product
from services.helpers import ValidationError, required, whitelist
from services.access_policy import authorize_object, has_permission


def can_review(principal, product_code):
    return bool(has_permission(principal, 'reviews.create_own') and has_purchased(principal.get('customerCode'), product_code))


def has_purchased(customer_code, product_code):
    return bool(customer_code and get_db().orders.find_one({
        'customerCode': customer_code, 'items.productCode': product_code,
        'status': {'$in': ['confirmed', 'completed']},
    }, {'_id': 1}))


def create_own(principal, data, *, order_code=None):
    from werkzeug.exceptions import Forbidden
    import secrets
    if not has_permission(principal, 'reviews.create_own'):
        raise Forbidden()
    if order_code is not None:
        from services.customer_account_service import order
        purchased_order = order(principal, order_code)
        if purchased_order.get('status') not in {'confirmed', 'completed'}:
            raise ValidationError('Chỉ được đánh giá khi đơn hàng đã xác nhận hoặc hoàn tất')
        if data.get('productCode') not in {line['productCode'] for line in purchased_order.get('items', [])}:
            raise ValidationError('Sản phẩm không thuộc đơn hàng này')
    allowed = {'reviewCode', 'productCode', 'customerCode', 'rating', 'content', 'title', 'images'}
    if set(data) - allowed or (data.get('customerCode') and data['customerCode'] != principal.get('customerCode')):
        raise ValidationError('Danh tính hoặc trường đánh giá không được phép')
    clean = dict(data)
    clean['customerCode'] = principal['customerCode']
    clean.setdefault('reviewCode', 'DANHGIA' + secrets.token_hex(12).upper())
    return create(clean, created_by=principal['_id'], order_code=order_code)


def moderate(principal, code, status):
    from werkzeug.exceptions import Forbidden
    row = repo.find_by_code(code)
    if not row:
        raise LookupError('Không tìm thấy đánh giá')
    if not authorize_object(principal, 'reviews.moderate', row):
        raise Forbidden()
    return set_status(code, status)


def create(data, *, created_by=None, order_code=None):
    whitelist(data, ['reviewCode', 'productCode', 'customerCode', 'rating', 'content', 'title', 'images'],
              number_fields=['rating'], list_fields=['images'])
    data = dict(data); required(data, ["reviewCode", "productCode", "customerCode", "rating", "content"])
    product, customer = find_product(data["productCode"]), find_customer(data["customerCode"])
    if not product: raise ValidationError("Sản phẩm không tồn tại")
    if not customer or customer.get('status') != 'active': raise ValidationError("Khách hàng không tồn tại hoặc ngừng hoạt động")
    try: rating = int(data["rating"])
    except (TypeError, ValueError): raise ValidationError("Điểm đánh giá phải là số")
    if rating not in range(1, 6) or float(data['rating']) != rating: raise ValidationError("Điểm đánh giá phải từ 1 đến 5")
    if not 1 <= len(data['content'].strip()) <= 5000 or len(data.get('title', '')) > 200:
        raise ValidationError('Tiêu đề tối đa 200 ký tự, nội dung từ 1 đến 5000 ký tự')
    purchased = has_purchased(customer['customerCode'], product['productCode'])
    if not purchased:
        raise ValidationError('Bạn chỉ có thể đánh giá sản phẩm đã mua trong đơn hàng đã xác nhận hoặc hoàn tất')
    document = {"reviewCode": data["reviewCode"], "productCode": product["productCode"], "customer": {"customerCode": customer["customerCode"], "customerName": customer["fullName"]}, "rating": rating, "title": data.get("title", ""), "content": data["content"], "images": data.get("images", []), "verifiedPurchase": purchased, "helpfulCount": 0, "status": "pending", "createdAt": datetime.now()}
    document['productName'] = product['name']
    document['productImage'] = product.get('image') or product.get('imageUrl')
    if created_by is not None:
        document['createdByUserId'] = created_by
    if order_code is not None:
        document['orderCode'] = order_code
    try: return repo.insert(document)
    except DuplicateKeyError as exc: raise ValidationError("Mã đánh giá đã tồn tại") from exc


def set_status(code, status):
    if status not in {"approved", "rejected"}: raise ValidationError("Trạng thái duyệt không hợp lệ")
    if not repo.find_by_code(code): raise LookupError("Không tìm thấy đánh giá")
    return repo.set_status(code, status)

