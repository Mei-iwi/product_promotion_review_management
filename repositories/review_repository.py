from db.mongo import get_db


def find_reviews(filters=None, approved_only=False):
    filters = filters or {}
    query = {"status": "approved"} if approved_only else {}
    for key in ("productCode", "status", "rating", "verifiedPurchase"):
        if filters.get(key) not in (None, ""):
            value = filters[key]
            if key == "rating": value = int(value)
            if key == "verifiedPurchase": value = str(value).lower() == "true"
            query[key] = value
    if filters.get("customerCode"):
        query["customer.customerCode"] = filters["customerCode"]
    return list(get_db().reviews.find(query).sort("createdAt", -1))


def find_by_code(code):
    return get_db().reviews.find_one({"reviewCode": code})


def insert(document):
    get_db().reviews.insert_one(document)
    return find_by_code(document["reviewCode"])


def set_status(code, status):
    get_db().reviews.update_one({"reviewCode": code}, {"$set": {"status": status}})
    return find_by_code(code)

