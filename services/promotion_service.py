from pymongo.errors import DuplicateKeyError
from repositories import promotion_repository as repo
from services.helpers import ValidationError, required, parse_date, whitelist
from services.shopping_common import VIETNAM, utc


def admin_date(value, field):
    value = parse_date(value, field)
    # Existing stored BSON Date values remain UTC instants. New timezone-less
    # admin inputs (datetime-local) are explicitly Vietnam time.
    if value.tzinfo is None:
        value = value.replace(tzinfo=VIETNAM)
    return utc(value).replace(tzinfo=None)


def validate(data, creating=False):
    whitelist(data, ['promoCode', 'name', 'promoType', 'value', 'startDate', 'endDate', 'status', 'conditions', 'targets', 'usageLimit'],
              object_fields=['conditions', 'targets'], number_fields=['value', 'usageLimit'])
    whitelist(data.get('conditions', {}), ['minOrderValue', 'maxDiscount'], number_fields=['minOrderValue', 'maxDiscount'])
    whitelist(data.get('targets', {}), ['productCodes', 'categories'], list_fields=['productCodes', 'categories'])
    for field in ['minOrderValue', 'maxDiscount']:
        if field in data.get('conditions', {}): data['conditions'][field] = float(data['conditions'][field])
    if 'usageLimit' in data: data['usageLimit'] = int(data['usageLimit'])
    required(data, (["promoCode"] if creating else []) + ["name", "promoType", "value", "startDate", "endDate", "status"])
    if data["promoType"] not in {"percentage", "fixed"}: raise ValidationError("Loại giảm không hợp lệ")
    data["value"] = float(data["value"])
    if data["value"] < 0 or (data["promoType"] == "percentage" and data["value"] > 100): raise ValidationError("Giá trị giảm không hợp lệ")
    data["startDate"], data["endDate"] = admin_date(data["startDate"], "startDate"), admin_date(data["endDate"], "endDate")
    try:
        if data["endDate"] < data["startDate"]: raise ValidationError("Ngày kết thúc phải sau ngày bắt đầu")
    except TypeError as exc:
        raise ValidationError('Hai ngày phải có cùng định dạng múi giờ') from exc
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

