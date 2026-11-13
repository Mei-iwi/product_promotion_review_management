from repositories.security_repository import utcnow
from db.mongo import get_db

OFFER_FIELDS = {'_id': 0, 'promoCode': 1, 'name': 1, 'promoType': 1, 'value': 1,
                'status': 1, 'startDate': 1, 'endDate': 1, 'conditions': 1,
                'targets': 1, 'usageLimit': 1, 'commerceUsed': 1}


def public_offers(page=None, size=12):
    query = {'status': 'active', 'endDate': {'$gte': utcnow()}}
    cursor = get_db().promotions.find(query, OFFER_FIELDS).sort([('endDate', 1), ('promoCode', 1)])
    if page is None:
        return list(cursor)
    return list(cursor.skip((page - 1) * size).limit(size)), get_db().promotions.count_documents(query)


def target_labels(promotions):
    codes = {c for p in promotions for c in p.get('targets', {}).get('productCodes', [])}
    categories = {c for p in promotions for c in p.get('targets', {}).get('categories', [])}
    rows = get_db().products.find({'$or': [{'productCode': {'$in': list(codes)}},
                                            {'category.categoryCode': {'$in': list(categories)}}]},
                                  {'_id': 0, 'productCode': 1, 'name': 1, 'category': 1})
    names, groups = {}, {}
    for row in rows:
        names[row['productCode']] = row['name']
        group = row.get('category', {})
        if group.get('categoryCode'):
            groups[group['categoryCode']] = group.get('categoryName', group['categoryCode'])
    return names, groups


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
        now = utcnow()
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
    now = utcnow()
    return list(get_db().promotions.find({"status": "active", "startDate": {"$lte": now}, "endDate": {"$gte": now}, "$or": [{"targets.productCodes": product["productCode"]}, {"targets.categories": product["category"]["categoryCode"]}]}))

