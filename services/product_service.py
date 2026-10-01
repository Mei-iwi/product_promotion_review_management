from pymongo.errors import DuplicateKeyError
from repositories import product_repository as repo
from services.helpers import ValidationError, required


def list_products(filters=None, page=1, per_page=10, sort=""):
    return repo.find_products(filters, max(1, int(page)), min(100, max(1, int(per_page))), sort)


def get_product(code):
    return repo.find_by_code(code)


def validate(data, creating=False):
    required(data, ["productCode", "name", "brand", "category", "price", "stock", "status"] if creating else ["name", "brand", "category", "price", "stock", "status"])
    category = data.get("category", {})
    if not isinstance(category, dict) or not category.get("categoryCode") or not category.get("categoryName"):
        raise ValidationError("Danh mục phải có mã và tên")
    for field in ("price", "stock"):
        try: data[field] = float(data[field]) if field == "price" else int(data[field])
        except (TypeError, ValueError): raise ValidationError(f"{field} phải là số")
        if data[field] < 0: raise ValidationError(f"{field} không được âm")
    if data["status"] not in {"active", "inactive"}: raise ValidationError("Trạng thái sản phẩm không hợp lệ")
    data.setdefault("attributes", {})
    data.setdefault("tags", [])
    return data


def create(data):
    clean = validate(dict(data), True); clean["createdByApp"] = True
    try: return repo.insert(clean)
    except DuplicateKeyError as exc: raise ValidationError("Mã sản phẩm đã tồn tại") from exc


def update(code, data):
    if not repo.find_by_code(code): raise LookupError("Không tìm thấy sản phẩm")
    clean = validate(dict(data)); clean.pop("productCode", None)
    return repo.update(code, clean)


def set_status(code, status):
    if status not in {"active", "inactive"}: raise ValidationError("Trạng thái không hợp lệ")
    if not repo.find_by_code(code): raise LookupError("Không tìm thấy sản phẩm")
    return repo.set_status(code, status)


def change_tag(code, tag, action):
    if not repo.find_by_code(code): raise LookupError("Không tìm thấy sản phẩm")
    if not str(tag).strip(): raise ValidationError("Nhãn không được trống")
    if action == "add": return repo.add_tag(code, str(tag).strip())
    if action == "remove": return repo.remove_tag(code, str(tag).strip())
    raise ValidationError("Thao tác nhãn không hợp lệ")


def delete(code):
    product = repo.find_by_code(code)
    if not product: raise LookupError("Không tìm thấy sản phẩm")
    if not product.get("createdByApp"): raise ValidationError("Chỉ được xóa sản phẩm thử do ứng dụng tạo")
    repo.delete(code)

