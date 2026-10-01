from db.mongo import get_db

VALID_ORDERS = {"$in": ["completed", "confirmed"]}


def summary():
    db = get_db()
    order_totals = list(db.orders.aggregate([
        {"$match": {"status": VALID_ORDERS}},
        {"$group": {"_id": None, "orders": {"$sum": 1}, "revenue": {"$sum": "$totalAmount"}, "discount": {"$sum": {"$ifNull": ["$appliedPromotion.discountAmount", 0]}}}},
    ]))
    rating = list(db.reviews.aggregate([{"$match": {"status": "approved"}}, {"$group": {"_id": None, "avg": {"$avg": "$rating"}}}]))
    totals = order_totals[0] if order_totals else {"orders": 0, "revenue": 0, "discount": 0}
    average = rating[0].get("avg") if rating else None
    return {"activeProducts": db.products.count_documents({"status": "active"}), "activePromotions": db.promotions.count_documents({"status": "active"}), "customers": db.customers.count_documents({}), "approvedReviews": db.reviews.count_documents({"status": "approved"}), "averageRating": round(average, 2) if average is not None else 0, "orders": totals.get("orders", 0), "revenue": totals.get("revenue", 0), "discount": totals.get("discount", 0)}


def nc01():
    return list(get_db().reviews.aggregate([{"$match": {"status": "approved"}}, {"$group": {"_id": "$productCode", "reviewCount": {"$sum": 1}, "avgRating": {"$avg": "$rating"}}}, {"$lookup": {"from": "products", "localField": "_id", "foreignField": "productCode", "as": "product"}}, {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}}, {"$project": {"_id": 0, "productCode": "$_id", "productName": {"$ifNull": ["$product.name", "Chưa xác định"]}, "reviewCount": 1, "avgRating": 1}}, {"$sort": {"avgRating": -1, "reviewCount": -1}}]))


def nc02():
    return list(get_db().reviews.aggregate([{"$match": {"status": "approved"}}, {"$group": {"_id": "$productCode", "reviewCount": {"$sum": 1}, "avgRating": {"$avg": "$rating"}}}, {"$match": {"reviewCount": {"$gte": 3}}}, {"$sort": {"avgRating": -1, "reviewCount": -1}}, {"$limit": 5}, {"$lookup": {"from": "products", "localField": "_id", "foreignField": "productCode", "as": "product"}}, {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}}, {"$project": {"_id": 0, "productCode": "$_id", "productName": {"$ifNull": ["$product.name", "Chưa xác định"]}, "reviewCount": 1, "avgRating": 1}}]))


def nc03():
    return list(get_db().reviews.aggregate([{"$match": {"status": "approved"}}, {"$group": {"_id": "$rating", "totalReviews": {"$sum": 1}}}, {"$sort": {"_id": 1}}, {"$project": {"_id": 0, "rating": "$_id", "totalReviews": 1}}]))


def nc04():
    return list(get_db().orders.aggregate([{"$match": {"status": VALID_ORDERS}}, {"$group": {"_id": "$customerCode", "orderCount": {"$sum": 1}, "totalRevenue": {"$sum": "$totalAmount"}}}, {"$sort": {"totalRevenue": -1}}, {"$lookup": {"from": "customers", "localField": "_id", "foreignField": "customerCode", "as": "customer"}}, {"$unwind": {"path": "$customer", "preserveNullAndEmptyArrays": True}}, {"$project": {"_id": 0, "customerCode": "$_id", "customerName": {"$ifNull": ["$customer.fullName", "Chưa xác định"]}, "orderCount": 1, "totalRevenue": 1}}]))


def nc05():
    return list(get_db().orders.aggregate([{"$match": {"status": VALID_ORDERS}}, {"$unwind": "$items"}, {"$group": {"_id": "$items.productCode", "productName": {"$first": "$items.productName"}, "quantitySold": {"$sum": "$items.quantity"}, "revenueBeforeDiscount": {"$sum": {"$multiply": ["$items.quantity", "$items.unitPrice"]}}}}, {"$sort": {"revenueBeforeDiscount": -1}}, {"$project": {"_id": 0, "productCode": "$_id", "productName": 1, "quantitySold": 1, "revenueBeforeDiscount": 1}}]))


def nc06():
    return list(get_db().orders.aggregate([{"$match": {"status": VALID_ORDERS}}, {"$unwind": "$items"}, {"$group": {"_id": "$items.productCode", "productName": {"$first": "$items.productName"}, "quantitySold": {"$sum": "$items.quantity"}}}, {"$sort": {"quantitySold": -1}}, {"$limit": 5}, {"$project": {"_id": 0, "productCode": "$_id", "productName": 1, "quantitySold": 1}}]))


def nc07():
    return list(get_db().orders.aggregate([{"$match": {"status": VALID_ORDERS, "appliedPromotion.promoCode": {"$exists": True, "$ne": None}}}, {"$group": {"_id": "$appliedPromotion.promoCode", "usageCount": {"$sum": 1}, "totalDiscount": {"$sum": "$appliedPromotion.discountAmount"}}}, {"$sort": {"totalDiscount": -1}}, {"$project": {"_id": 0, "promoCode": "$_id", "usageCount": 1, "totalDiscount": 1}}]))


def nc08():
    return list(get_db().orders.aggregate([{"$match": {"status": VALID_ORDERS}}, {"$group": {"_id": {"year": {"$year": "$orderDate"}, "month": {"$month": "$orderDate"}}, "orderCount": {"$sum": 1}, "revenue": {"$sum": "$totalAmount"}}}, {"$sort": {"_id.year": 1, "_id.month": 1}}, {"$project": {"_id": 0, "year": "$_id.year", "month": "$_id.month", "orderCount": 1, "revenue": 1}}]))


def nc09():
    return list(get_db().reviews.aggregate([{"$match": {"status": "approved"}}, {"$group": {"_id": "$productCode", "reviewCount": {"$sum": 1}, "avgRating": {"$avg": "$rating"}}}, {"$lookup": {"from": "products", "localField": "_id", "foreignField": "productCode", "as": "product"}}, {"$unwind": "$product"}, {"$project": {"_id": 0, "productCode": "$_id", "productName": "$product.name", "reviewCount": 1, "avgRating": 1}}, {"$sort": {"avgRating": -1}}]))


def nc10():
    return list(get_db().reviews.aggregate([{"$match": {"status": "approved"}}, {"$group": {"_id": {"customerCode": "$customer.customerCode", "customerName": "$customer.customerName"}, "totalReviews": {"$sum": 1}}}, {"$sort": {"totalReviews": -1}}, {"$limit": 10}, {"$project": {"_id": 0, "customerCode": "$_id.customerCode", "customerName": "$_id.customerName", "totalReviews": 1}}]))


AGGREGATIONS = {f"NC{i:02}": fn for i, fn in enumerate([nc01, nc02, nc03, nc04, nc05, nc06, nc07, nc08, nc09, nc10], 1)}


def run_basic(code):
    db = get_db()
    queries = {
        "CB01": lambda: list(db.products.find({"status": "active"})),
        "CB02": lambda: list(db.products.find({"category.categoryCode": "DM-PHUKIEN"})),
        "CB03": lambda: list(db.products.find({"price": {"$gte": 2000000, "$lte": 10000000}})),
        "CB04": lambda: list(db.products.find({"brand": {"$in": ["Apple", "Samsung"]}})),
        "CB05": lambda: list(db.products.find({"name": {"$regex": "Laptop", "$options": "i"}})),
        "CB06": lambda: list(db.products.find({"status": "active"}, {"_id": 0, "productCode": 1, "name": 1, "brand": 1, "price": 1})),
        "CB07": lambda: list(db.products.find({"tags": "văn phòng"})),
        "CB08": lambda: list(db.reviews.find({"productCode": "SANPHAM2026090001", "rating": {"$gte": 4}})),
        "CB09": lambda: list(db.orders.find({"customerCode": "KHACHHANG20260001"}).sort("orderDate", -1)),
        "CB10": lambda: list(db.products.find({}).sort("price", -1).limit(5)),
        "CB11": lambda: list(db.orders.find({"items.productCode": "SANPHAM2026090007"})),
        "CB12": lambda: list(db.reviews.find({"verifiedPurchase": True, "rating": {"$gte": 4}})),
    }
    if code in queries: return queries[code]()
    if code in AGGREGATIONS: return AGGREGATIONS[code]()
    raise KeyError(code)

