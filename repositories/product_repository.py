from db.mongo import get_db
import re


def find_products(filters=None, page=1, per_page=10, sort=""):
    filters = filters or {}
    query = {}
    if filters.get("q"):
        query["name"] = {"$regex": re.escape(filters["q"][:200]), "$options": "i"}
    mappings = {"category": "category.categoryCode", "brand": "brand", "status": "status", "tag": "tags"}
    for source, target in mappings.items():
        if filters.get(source):
            query[target] = filters[source]
    if filters.get("min_price") not in (None, "") or filters.get("max_price") not in (None, ""):
        query["price"] = {}
        if filters.get("min_price") not in (None, ""):
            query["price"]["$gte"] = float(filters["min_price"])
        if filters.get("max_price") not in (None, ""):
            query["price"]["$lte"] = float(filters["max_price"])
    direction = -1 if sort == "price_desc" else 1
    cursor = get_db().products.find(query).sort("price", direction).skip((page - 1) * per_page).limit(per_page)
    return list(cursor), get_db().products.count_documents(query)


def find_by_code(code):
    return get_db().products.find_one({"productCode": code})


def insert(document):
    get_db().products.insert_one(document)
    return find_by_code(document["productCode"])


def update(code, document):
    get_db().products.update_one({"productCode": code}, {"$set": document})
    return find_by_code(code)


def set_status(code, status):
    return update(code, {"status": status})


def add_tag(code, tag):
    get_db().products.update_one({"productCode": code}, {"$addToSet": {"tags": tag}})
    return find_by_code(code)


def remove_tag(code, tag):
    get_db().products.update_one({"productCode": code}, {"$pull": {"tags": tag}})
    return find_by_code(code)


def delete(code):
    return get_db().products.delete_one({"productCode": code, "createdByApp": True}).deleted_count

