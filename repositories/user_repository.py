"""Account reads always receive a server-built, already-scoped query."""
from db.mongo import get_db

PUBLIC_FIELDS = {'_id': 1, 'email': 1, 'role': 1, 'status': 1, 'customerCode': 1,
                 'createdAt': 1, 'updatedAt': 1, 'lastLoginAt': 1, 'lockedUntil': 1}


def list_users(query, page=None, per_page=10):
    total = get_db().users.count_documents(query)
    cursor = get_db().users.find(query, PUBLIC_FIELDS).sort([('emailNormalized', 1), ('_id', 1)])
    if page is not None:
        cursor = cursor.skip((page - 1) * per_page).limit(per_page)
    return list(cursor), total


def find_scoped(user_id, scope):
    return get_db().users.find_one({**scope, '_id': user_id})
