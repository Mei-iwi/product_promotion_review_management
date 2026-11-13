from db.mongo import get_db
from services.helpers import ValidationError


def find_reviews(filters=None, approved_only=False):
    filters = filters or {}
    query = {"status": "approved"} if approved_only else {}
    for key in ("productCode", "status", "rating", "verifiedPurchase"):
        if filters.get(key) not in (None, ""):
            value = filters[key]
            if key == "rating":
                try: value = int(value)
                except (ValueError, TypeError) as exc: raise ValidationError('Điểm lọc không hợp lệ') from exc
                if value not in range(1, 6): raise ValidationError('Điểm lọc không hợp lệ')
            if key == "verifiedPurchase": value = str(value).lower() == "true"
            query[key] = value
    if filters.get("customerCode"):
        query["customer.customerCode"] = filters["customerCode"]
    return list(get_db().reviews.find(query).sort("createdAt", -1))


def find_by_code(code):
    return get_db().reviews.find_one({"reviewCode": code})


def reviewed_products(codes):
    rows = get_db().products.find({'productCode': {'$in': list(codes)}},
                                  {'_id': 0, 'productCode': 1, 'name': 1, 'image': 1, 'imageUrl': 1, 'status': 1})
    return {row['productCode']: row for row in rows}


def insert(document):
    get_db().reviews.insert_one(document)
    return find_by_code(document["reviewCode"])


def set_status(code, status):
    get_db().reviews.update_one({"reviewCode": code}, {"$set": {"status": status}})
    return find_by_code(code)

