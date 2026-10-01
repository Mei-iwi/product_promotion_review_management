from datetime import datetime
from pymongo.errors import DuplicateKeyError
from db.mongo import get_db
from repositories import review_repository as repo
from repositories.customer_repository import find_by_code as find_customer
from repositories.product_repository import find_by_code as find_product
from services.helpers import ValidationError, required


def create(data):
    data = dict(data); required(data, ["reviewCode", "productCode", "customerCode", "rating", "content"])
    product, customer = find_product(data["productCode"]), find_customer(data["customerCode"])
    if not product: raise ValidationError("Sản phẩm không tồn tại")
    if not customer: raise ValidationError("Khách hàng không tồn tại")
    try: rating = int(data["rating"])
    except (TypeError, ValueError): raise ValidationError("Điểm đánh giá phải là số")
    if rating not in range(1, 6): raise ValidationError("Điểm đánh giá phải từ 1 đến 5")
    purchased = get_db().orders.count_documents({"customerCode": customer["customerCode"], "items.productCode": product["productCode"], "status": {"$in": ["confirmed", "completed"]}}) > 0
    document = {"reviewCode": data["reviewCode"], "productCode": product["productCode"], "customer": {"customerCode": customer["customerCode"], "customerName": customer["fullName"]}, "rating": rating, "title": data.get("title", ""), "content": data["content"], "images": data.get("images", []), "verifiedPurchase": purchased, "helpfulCount": 0, "status": "pending", "createdAt": datetime.now()}
    try: return repo.insert(document)
    except DuplicateKeyError as exc: raise ValidationError("Mã đánh giá đã tồn tại") from exc


def set_status(code, status):
    if status not in {"approved", "rejected"}: raise ValidationError("Trạng thái duyệt không hợp lệ")
    if not repo.find_by_code(code): raise LookupError("Không tìm thấy đánh giá")
    return repo.set_status(code, status)

