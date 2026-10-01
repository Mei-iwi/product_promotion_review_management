from pymongo.errors import DuplicateKeyError
from repositories import promotion_repository as repo
from services.helpers import ValidationError, required, parse_date


def validate(data, creating=False):
    required(data, (["promoCode"] if creating else []) + ["name", "promoType", "value", "startDate", "endDate", "status"])
    if data["promoType"] not in {"percentage", "fixed"}: raise ValidationError("Loại giảm không hợp lệ")
    data["value"] = float(data["value"])
    if data["value"] < 0 or (data["promoType"] == "percentage" and data["value"] > 100): raise ValidationError("Giá trị giảm không hợp lệ")
    data["startDate"], data["endDate"] = parse_date(data["startDate"], "startDate"), parse_date(data["endDate"], "endDate")
    if data["endDate"] < data["startDate"]: raise ValidationError("Ngày kết thúc phải sau ngày bắt đầu")
    data.setdefault("conditions", {"minOrderValue": 0, "maxDiscount": 0}); data.setdefault("targets", {"productCodes": [], "categories": []})
    if min(data["conditions"].get("minOrderValue", 0), data["conditions"].get("maxDiscount", 0), data.get("usageLimit", 0)) < 0: raise ValidationError("Điều kiện khuyến mãi không được âm")
    if data["status"] not in {"active", "expired", "inactive"}: raise ValidationError("Trạng thái không hợp lệ")
    return data


def create(data):
    try: return repo.insert(validate(dict(data), True))
    except DuplicateKeyError as exc: raise ValidationError("Mã khuyến mãi đã tồn tại") from exc


def update(code, data):
    if not repo.find_by_code(code): raise LookupError("Không tìm thấy khuyến mãi")
    clean = validate(dict(data)); clean.pop("promoCode", None)
    return repo.update(code, clean)

