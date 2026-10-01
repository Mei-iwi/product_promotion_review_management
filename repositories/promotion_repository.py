from datetime import datetime
from db.mongo import get_db


def find_promotions(filters=None):
    filters = filters or {}
    query = {}
    for key in ("status", "promoType"):
        if filters.get(key):
            query[key] = filters[key]
    if filters.get("category"):
        query["targets.categories"] = filters["category"]
    if filters.get("productCode"):
        query["targets.productCodes"] = filters["productCode"]
    if filters.get("valid"):
        now = datetime.now()
        query.update({"status": "active", "startDate": {"$lte": now}, "endDate": {"$gte": now}})
    return list(get_db().promotions.find(query).sort("startDate", -1))


def find_by_code(code):
    return get_db().promotions.find_one({"promoCode": code})


def insert(document):
    get_db().promotions.insert_one(document)
    return find_by_code(document["promoCode"])


def update(code, document):
    get_db().promotions.update_one({"promoCode": code}, {"$set": document})
    return find_by_code(code)


def applicable_for(product):
    now = datetime.now()
    return list(get_db().promotions.find({"status": "active", "startDate": {"$lte": now}, "endDate": {"$gte": now}, "$or": [{"targets.productCodes": product["productCode"]}, {"targets.categories": product["category"]["categoryCode"]}]}))

