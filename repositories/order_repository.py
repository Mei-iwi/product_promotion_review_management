from db.mongo import get_db
from datetime import datetime


def find_orders(filters=None):
    filters = filters or {}
    query = {}
    if filters.get("customerCode"): query["customerCode"] = filters["customerCode"]
    if filters.get("status"): query["status"] = filters["status"]
    if filters.get("productCode"): query["items.productCode"] = filters["productCode"]
    if filters.get("promotion") == "yes": query["appliedPromotion"] = {"$ne": None}
    if filters.get("promotion") == "no": query["appliedPromotion"] = None
    dates = {}
    if filters.get("from_date"): dates["$gte"] = datetime.fromisoformat(str(filters["from_date"]))
    if filters.get("to_date"): dates["$lte"] = datetime.fromisoformat(str(filters["to_date"]))
    if dates: query["orderDate"] = dates
    return list(get_db().orders.find(query).sort("orderDate", -1))


def find_by_code(code):
    return get_db().orders.find_one({"orderCode": code})

