from db.mongo import get_db
import re


def find_customers(filters=None):
    filters = filters or {}
    query = {}
    if filters.get("q"):
        query["$or"] = [{"fullName": {"$regex": re.escape(filters["q"][:200]), "$options": "i"}}, {"email": {"$regex": re.escape(filters["q"][:200]), "$options": "i"}}]
    for key in ("level", "status"):
        if filters.get(key):
            query[key] = filters[key]
    return list(get_db().customers.find(query).sort("joinedAt", -1))


def find_by_code(code):
    return get_db().customers.find_one({"customerCode": code})


def insert(document):
    get_db().customers.insert_one(document)
    return find_by_code(document["customerCode"])


def update(code, document):
    get_db().customers.update_one({"customerCode": code}, {"$set": document})
    return find_by_code(code)

