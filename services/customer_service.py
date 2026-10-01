import re
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from repositories import customer_repository as repo
from services.helpers import ValidationError, required, parse_date


def validate(data, creating=False):
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
    try: return repo.update(code, clean)
    except DuplicateKeyError as exc: raise ValidationError("Email đã tồn tại") from exc

