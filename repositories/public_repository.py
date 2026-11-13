from db.mongo import get_db

PRODUCT_FIELDS = {'_id': 0, 'productCode': 1, 'name': 1, 'brand': 1, 'category': 1, 'price': 1,
                  'image': {'$ifNull': ['$image', '$imageUrl']},
                  'inStock': {'$gt': [{'$ifNull': ['$stock', 0]}, 0]}}
PUBLIC_ATTRIBUTES = ['storage', 'ram', 'processor', 'screen', 'color', 'connectivity', 'capacity',
                     'ports', 'condition', 'model', 'battery', 'warranty']
REVIEW_FIELDS = {'_id': 0, 'rating': 1, 'title': 1, 'content': 1, 'createdAt': 1, 'verifiedPurchase': 1}


def products():
    return page({'status': 'active'}, [('name', 1), ('productCode', 1)], 1, 100)[0]


def page(query, sort, number, size):
    pipeline = [{'$match': query}, {'$sort': dict(sort)}, {'$skip': (number - 1) * size},
                {'$limit': size}, {'$project': PRODUCT_FIELDS}]
    return list(get_db().products.aggregate(pipeline)), get_db().products.count_documents(query)


def options():
    db = get_db()
    categories = list(db.products.aggregate([{'$match': {'status': 'active'}},
                       {'$group': {'_id': '$category.categoryCode', 'name': {'$first': '$category.categoryName'}}}, {'$sort': {'name': 1}}]))
    return {'brands': sorted(db.products.distinct('brand', {'status': 'active'})), 'categories': categories}


def ratings(codes):
    return {row['_id']: row for row in get_db().reviews.aggregate([
        {'$match': {'productCode': {'$in': codes}, 'status': 'approved'}},
        {'$group': {'_id': '$productCode', 'avgRating': {'$avg': '$rating'}, 'reviewCount': {'$sum': 1}}}])}


def product(code):
    fields = {**PRODUCT_FIELDS, **{'attributes.' + key: 1 for key in PUBLIC_ATTRIBUTES}}
    rows = list(get_db().products.aggregate([{'$match': {'productCode': code, 'status': 'active'}}, {'$limit': 1}, {'$project': fields}]))
    return rows[0] if rows else None


def reviews(code):
    if not product(code):
        return None
    return list(get_db().reviews.find({'productCode': code, 'status': 'approved'}, REVIEW_FIELDS).sort('createdAt', -1).limit(100))


def review_choices(customer_code, selected=None):
    bought = get_db().orders.find({'customerCode': customer_code, 'status': {'$in': ['confirmed', 'completed']}}, {'items.productCode': 1})
    codes = {item['productCode'] for order in bought for item in order.get('items', [])}
    query = {'productCode': {'$in': list(codes)}}
    projection = {'_id': 0, 'productCode': 1, 'name': 1}
    rows = list(get_db().products.find(query, projection).sort('name', 1).limit(500))
    if isinstance(selected, str) and len(selected) <= 80 and selected not in {p['productCode'] for p in rows}:
        row = get_db().products.find_one({'$and': [query, {'productCode': selected}]}, projection)
        if row:
            rows.append(row)
    return rows
