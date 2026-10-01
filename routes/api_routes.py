from flask import Blueprint, jsonify, request
from pymongo.errors import PyMongoError
from repositories.common import serialize
from repositories import customer_repository, promotion_repository, review_repository
from services import product_service, customer_service, promotion_service, review_service, order_service, dashboard_service
from services.helpers import ValidationError

bp = Blueprint("api", __name__, url_prefix="/api")


def response(data=None, message="Thành công", status=200, success=True):
    return jsonify({"success": success, "message": message, "data": serialize(data)}), status


def body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict): raise ValidationError("Dữ liệu JSON không hợp lệ")
    return value


@bp.errorhandler(ValidationError)
def validation_error(error): return response(None, str(error), 400, False)


@bp.errorhandler(LookupError)
def lookup_error(error): return response(None, str(error), 404, False)


@bp.errorhandler(PyMongoError)
def database_error(error): return response(None, "Không thể xử lý dữ liệu MongoDB", 500, False)


@bp.get("/products")
def products():
    rows, total = product_service.list_products(request.args, request.args.get("page", 1), request.args.get("per_page", 10), request.args.get("sort", ""))
    return response({"items": rows, "total": total})


@bp.get("/products/<code>")
def product(code):
    row = product_service.get_product(code)
    return response(row) if row else response(None, "Không tìm thấy sản phẩm", 404, False)


@bp.post("/products")
def create_product(): return response(product_service.create(body()), "Đã thêm sản phẩm", 201)


@bp.put("/products/<code>")
def update_product(code): return response(product_service.update(code, body()), "Đã cập nhật sản phẩm")


@bp.patch("/products/<code>/status")
def product_status(code): return response(product_service.set_status(code, body().get("status")), "Đã cập nhật trạng thái")


@bp.patch("/products/<code>/tags")
def product_tags(code):
    data = body(); return response(product_service.change_tag(code, data.get("tag"), data.get("action")), "Đã cập nhật nhãn")


@bp.delete("/products/<code>")
def delete_product(code):
    product_service.delete(code); return response(None, "Đã xóa sản phẩm thử")


@bp.get("/promotions")
def promotions(): return response(promotion_repository.find_promotions(request.args))


@bp.get("/promotions/<code>")
def promotion(code):
    row = promotion_repository.find_by_code(code)
    return response(row) if row else response(None, "Không tìm thấy khuyến mãi", 404, False)


@bp.post("/promotions")
def create_promotion(): return response(promotion_service.create(body()), "Đã thêm khuyến mãi", 201)


@bp.put("/promotions/<code>")
def update_promotion(code): return response(promotion_service.update(code, body()), "Đã cập nhật khuyến mãi")


@bp.get("/customers")
def customers(): return response(customer_repository.find_customers(request.args))


@bp.get("/customers/<code>")
def customer(code):
    row = customer_repository.find_by_code(code)
    return response(row) if row else response(None, "Không tìm thấy khách hàng", 404, False)


@bp.post("/customers")
def create_customer(): return response(customer_service.create(body()), "Đã thêm khách hàng", 201)


@bp.put("/customers/<code>")
def update_customer(code): return response(customer_service.update(code, body()), "Đã cập nhật khách hàng")


@bp.get("/reviews")
def reviews(): return response(review_repository.find_reviews(request.args))


@bp.post("/reviews")
def create_review(): return response(review_service.create(body()), "Đã gửi đánh giá và đang chờ duyệt", 201)


@bp.patch("/reviews/<code>/status")
def review_status(code): return response(review_service.set_status(code, body().get("status")), "Đã cập nhật trạng thái đánh giá")


@bp.get("/orders")
def orders(): return response(order_service.list_orders(request.args))


@bp.get("/orders/<code>")
def order(code):
    row = order_service.get_order(code)
    return response(row) if row else response(None, "Không tìm thấy đơn hàng", 404, False)


@bp.get("/dashboard/summary")
def dashboard_summary(): return response(dashboard_service.get_summary())


@bp.get("/dashboard/ratings")
def dashboard_ratings(): return response(dashboard_service.get_ratings())


@bp.get("/dashboard/promotions")
def dashboard_promotions(): return response(dashboard_service.get_promotions())


@bp.get("/dashboard/sales")
def dashboard_sales(): return response(dashboard_service.get_sales())

