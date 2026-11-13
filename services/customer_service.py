import re
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from repositories import customer_repository as repo
from services.helpers import ValidationError, required, parse_date, whitelist


def validate(data, creating=False):
    whitelist(data, ['customerCode', 'fullName', 'email', 'address', 'level', 'status', 'joinedAt'])
    required(data, (["customerCode"] if creating else []) + ["fullName", "email", "level", "status"])
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", data["email"]): raise ValidationError("Email không hợp lệ")
    if data["level"] not in {"normal", "silver", "gold"}: raise ValidationError("Hạng khách hàng không hợp lệ")
    if data["status"] not in {"active", "inactive"}: raise ValidationError("Trạng thái không hợp lệ")
    data["joinedAt"] = parse_date(data.get("joinedAt", datetime.now()), "joinedAt")
    return data


def create(data):
    try: return repo.insert(validate(dict(data), True))
    except DuplicateKeyError as exc: raise ValidationError("Mã khách hàng hoặc email đã tồn tại") from exc


def update(code, data):
    if not repo.find_by_code(code): raise LookupError("Không tìm thấy khách hàng")
    clean = validate(dict(data)); clean.pop("customerCode", None)
    try:
        row = repo.update(code, clean)
        if clean['status'] == 'inactive':
            from db.mongo import get_db
            from repositories.security_repository import revoke_user
            users = list(get_db().users.find({'role': 'CUSTOMER', 'customerCode': code}, {'_id': 1}))
            for user in users:
                get_db().users.update_one({'_id': user['_id']}, {'$inc': {'authVersion': 1}})
                revoke_user(user['_id'])
        return row
    except DuplicateKeyError as exc: raise ValidationError("Email đã tồn tại") from exc

