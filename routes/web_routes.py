from datetime import datetime
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, g
from services.access_policy import has_permission, REPORT_PERMISSIONS
from db.mongo import get_db
from repositories import customer_repository, promotion_repository, review_repository, report_repository
from repositories.common import serialize
from services import product_service, promotion_service, customer_service, order_service, review_service
from services.helpers import ValidationError

bp = Blueprint("web", __name__)

REPORTS = {
    "NC05": {"group": "Kinh doanh", "title": "Doanh thu theo sản phẩm", "description": "Theo dõi số lượng bán và doanh thu trước giảm giá.", "columns": [("productCode", "Mã sản phẩm", "text"), ("productName", "Sản phẩm", "text"), ("quantitySold", "Đã bán", "number"), ("revenueBeforeDiscount", "Doanh thu", "money")]},
    "NC08": {"group": "Kinh doanh", "title": "Doanh thu theo tháng", "description": "Tổng hợp số đơn và doanh thu theo từng tháng.", "columns": [("monthLabel", "Thời gian", "text"), ("orderCount", "Số đơn", "number"), ("revenue", "Doanh thu", "money")]},
    "NC04": {"group": "Kinh doanh", "title": "Doanh thu theo khách hàng", "description": "Xác định khách hàng có giá trị mua hàng cao.", "columns": [("customerCode", "Mã khách hàng", "text"), ("customerName", "Khách hàng", "text"), ("orderCount", "Số đơn", "number"), ("totalRevenue", "Doanh thu", "money")]},
    "NC06": {"group": "Kinh doanh", "title": "Sản phẩm bán chạy", "description": "Năm sản phẩm có số lượng bán cao nhất.", "columns": [("productCode", "Mã sản phẩm", "text"), ("productName", "Sản phẩm", "text"), ("quantitySold", "Đã bán", "number")]},
    "NC07": {"group": "Khuyến mãi", "title": "Hiệu quả chương trình khuyến mãi", "description": "So sánh lượt sử dụng và tổng tiền giảm của từng chương trình.", "columns": [("promoCode", "Mã khuyến mãi", "text"), ("usageCount", "Lượt sử dụng", "number"), ("totalDiscount", "Tổng tiền giảm", "money")]},
    "NC01": {"group": "Đánh giá", "title": "Điểm đánh giá theo sản phẩm", "description": "Điểm trung bình và số lượt đánh giá đã duyệt của mỗi sản phẩm.", "columns": [("productCode", "Mã sản phẩm", "text"), ("productName", "Sản phẩm", "text"), ("reviewCount", "Lượt đánh giá", "number"), ("avgRating", "Điểm trung bình", "rating")]},
    "NC02": {"group": "Đánh giá", "title": "Sản phẩm được đánh giá cao", "description": "Các sản phẩm nổi bật có từ ba đánh giá đã duyệt.", "columns": [("productCode", "Mã sản phẩm", "text"), ("productName", "Sản phẩm", "text"), ("reviewCount", "Lượt đánh giá", "number"), ("avgRating", "Điểm trung bình", "rating")]},
    "NC03": {"group": "Đánh giá", "title": "Phân bố mức đánh giá", "description": "Số lượng đánh giá tương ứng từ một đến năm sao.", "columns": [("rating", "Mức đánh giá", "stars"), ("totalReviews", "Số đánh giá", "number")]},
    "NC09": {"group": "Đánh giá", "title": "Chất lượng sản phẩm", "description": "Đối chiếu tên sản phẩm, điểm trung bình và số lượt đánh giá.", "columns": [("productCode", "Mã sản phẩm", "text"), ("productName", "Sản phẩm", "text"), ("reviewCount", "Lượt đánh giá", "number"), ("avgRating", "Điểm trung bình", "rating")]},
    "NC10": {"group": "Đánh giá", "title": "Khách hàng tích cực đánh giá", "description": "Khách hàng có số lượt gửi đánh giá nhiều nhất.", "columns": [("customerCode", "Mã khách hàng", "text"), ("customerName", "Khách hàng", "text"), ("totalReviews", "Số đánh giá", "number")]},
    "CB01": {"group": "Danh mục sản phẩm", "title": "Sản phẩm đang kinh doanh", "description": "Danh sách sản phẩm đang hoạt động trong hệ thống.", "columns": [("productCode", "Mã sản phẩm", "text"), ("name", "Sản phẩm", "text"), ("brand", "Thương hiệu", "text"), ("price", "Giá bán", "money"), ("stock", "Tồn kho", "number")]},
    "CB02": {"group": "Danh mục sản phẩm", "title": "Sản phẩm phụ kiện", "description": "Danh sách sản phẩm thuộc nhóm phụ kiện.", "columns": [("productCode", "Mã sản phẩm", "text"), ("name", "Sản phẩm", "text"), ("brand", "Thương hiệu", "text"), ("price", "Giá bán", "money"), ("stock", "Tồn kho", "number")]},
    "CB03": {"group": "Danh mục sản phẩm", "title": "Sản phẩm trong khoảng giá phổ biến", "description": "Sản phẩm có giá từ 2 đến 10 triệu đồng.", "columns": [("productCode", "Mã sản phẩm", "text"), ("name", "Sản phẩm", "text"), ("brand", "Thương hiệu", "text"), ("price", "Giá bán", "money"), ("stock", "Tồn kho", "number")]},
    "CB04": {"group": "Danh mục sản phẩm", "title": "Sản phẩm Apple và Samsung", "description": "Danh sách sản phẩm theo hai thương hiệu chính.", "columns": [("productCode", "Mã sản phẩm", "text"), ("name", "Sản phẩm", "text"), ("brand", "Thương hiệu", "text"), ("price", "Giá bán", "money")]},
    "CB05": {"group": "Danh mục sản phẩm", "title": "Danh mục laptop", "description": "Các sản phẩm có tên chứa từ khóa Laptop.", "columns": [("productCode", "Mã sản phẩm", "text"), ("name", "Sản phẩm", "text"), ("brand", "Thương hiệu", "text"), ("price", "Giá bán", "money"), ("stock", "Tồn kho", "number")]},
    "CB06": {"group": "Danh mục sản phẩm", "title": "Bảng giá sản phẩm", "description": "Danh mục rút gọn phục vụ tra cứu giá bán.", "columns": [("productCode", "Mã sản phẩm", "text"), ("name", "Sản phẩm", "text"), ("brand", "Thương hiệu", "text"), ("price", "Giá bán", "money")]},
    "CB07": {"group": "Danh mục sản phẩm", "title": "Thiết bị dành cho văn phòng", "description": "Sản phẩm được gắn nhãn văn phòng.", "columns": [("productCode", "Mã sản phẩm", "text"), ("name", "Sản phẩm", "text"), ("brand", "Thương hiệu", "text"), ("price", "Giá bán", "money"), ("stock", "Tồn kho", "number")]},
    "CB08": {"group": "Tra cứu hoạt động", "title": "Đánh giá tốt của sản phẩm nổi bật", "description": "Các đánh giá từ bốn sao của sản phẩm tiêu biểu.", "columns": [("reviewCode", "Mã đánh giá", "text"), ("customer.customerName", "Khách hàng", "text"), ("rating", "Mức đánh giá", "stars"), ("content", "Nội dung", "text"), ("createdAt", "Ngày đánh giá", "date")]},
    "CB09": {"group": "Tra cứu hoạt động", "title": "Lịch sử mua hàng của khách hàng", "description": "Các đơn gần nhất của khách hàng tiêu biểu.", "columns": [("orderCode", "Mã đơn", "text"), ("customerCode", "Mã khách hàng", "text"), ("orderDate", "Ngày đặt", "date"), ("totalAmount", "Tổng tiền", "money"), ("status", "Trạng thái", "status")]},
    "CB10": {"group": "Danh mục sản phẩm", "title": "Sản phẩm có giá cao nhất", "description": "Năm sản phẩm có giá niêm yết cao nhất.", "columns": [("productCode", "Mã sản phẩm", "text"), ("name", "Sản phẩm", "text"), ("brand", "Thương hiệu", "text"), ("price", "Giá bán", "money"), ("stock", "Tồn kho", "number")]},
    "CB11": {"group": "Tra cứu hoạt động", "title": "Đơn hàng có sản phẩm nổi bật", "description": "Các đơn hàng chứa sản phẩm tiêu biểu.", "columns": [("orderCode", "Mã đơn", "text"), ("customerCode", "Mã khách hàng", "text"), ("orderDate", "Ngày đặt", "date"), ("totalAmount", "Tổng tiền", "money"), ("status", "Trạng thái", "status")]},
    "CB12": {"group": "Tra cứu hoạt động", "title": "Đánh giá tốt từ người đã mua hàng", "description": "Đánh giá từ bốn sao, đã xác minh mua hàng.", "columns": [("reviewCode", "Mã đánh giá", "text"), ("productCode", "Mã sản phẩm", "text"), ("customer.customerName", "Khách hàng", "text"), ("rating", "Mức đánh giá", "stars"), ("content", "Nội dung", "text")]},
}


def _report_cell(row, path):
    value = row
    for key in path.split("."):
        value = value.get(key) if isinstance(value, dict) else None
    return value


@bp.get("/")
def home(): return render_template("home.html", summary=report_repository.summary())


@bp.get("/san-pham")
def products():
    rows, total = product_service.list_products(request.args, request.args.get("page", 1), 10, request.args.get("sort", ""))
    page = int(request.args.get("page", 1))
    return render_template("products/list.html", rows=rows, total=total, page=page, pages=max(1, (total + 9) // 10),
                           page_url=lambda p: url_for('web.products', **dict(request.args.to_dict(), page=p)))


def product_form_data(form, code=None):
    attributes = {}
    for line in form.get("attributes", "").splitlines():
        if "=" in line:
            key, value = line.split("=", 1); attributes[key.strip()] = value.strip()
    return {"productCode": code or form.get("productCode"), "name": form.get("name"), "brand": form.get("brand"), "category": {"categoryCode": form.get("categoryCode"), "categoryName": form.get("categoryName")}, "price": form.get("price"), "stock": form.get("stock"), "attributes": attributes, "tags": [x.strip() for x in form.get("tags", "").split(",") if x.strip()], "status": form.get("status")}


@bp.route("/san-pham/them", methods=["GET", "POST"])
def product_create_form():
    if request.method == "POST":
        try: product_service.create(product_form_data(request.form)); flash("Đã thêm sản phẩm", "success"); return redirect(url_for("web.products"))
        except ValidationError as error: flash(str(error), "danger")
    return render_template("products/form.html", item=None)


@bp.route("/san-pham/<code>/sua", methods=["GET", "POST"])
def product_edit_form(code):
    item = product_service.get_product(code)
    if not item: abort(404)
    if request.method == "POST":
        try: product_service.update(code, product_form_data(request.form, code)); flash("Đã cập nhật sản phẩm", "success"); return redirect(url_for("web.product_detail", code=code))
        except ValidationError as error: flash(str(error), "danger")
    return render_template("products/form.html", item=item)


@bp.get("/san-pham/<code>")
def product_detail(code):
    product = product_service.get_product(code)
    if not product: abort(404)
    reviews = review_repository.find_reviews({"productCode": code}, True)
    average = round(sum(r["rating"] for r in reviews) / len(reviews), 2) if reviews else 0
    promotions = promotion_repository.applicable_for(product) if has_permission(g.current_user, 'promotions.read') else []
    return render_template("products/detail.html", item=product, reviews=reviews, average=average, promotions=promotions)


@bp.get("/khuyen-mai")
def promotions(): return render_template("promotions/list.html", rows=promotion_repository.find_promotions(request.args))


def promotion_form_data(form, code=None):
    return {"promoCode": code or form.get("promoCode"), "name": form.get("name"), "promoType": form.get("promoType"), "value": form.get("value"), "startDate": form.get("startDate"), "endDate": form.get("endDate"), "conditions": {"minOrderValue": float(form.get("minOrderValue") or 0), "maxDiscount": float(form.get("maxDiscount") or 0)}, "targets": {"productCodes": [x.strip() for x in form.get("productCodes", "").split(",") if x.strip()], "categories": [x.strip() for x in form.get("categories", "").split(",") if x.strip()]}, "usageLimit": int(form.get("usageLimit") or 0), "status": form.get("status")}


@bp.route("/khuyen-mai/them", methods=["GET", "POST"])
def promotion_create_form():
    if request.method == "POST":
        try: promotion_service.create(promotion_form_data(request.form)); flash("Đã thêm khuyến mãi", "success"); return redirect(url_for("web.promotions"))
        except (ValidationError, ValueError) as error: flash(str(error), "danger")
    return render_template("promotions/form.html", item=None)


@bp.route("/khuyen-mai/<code>/sua", methods=["GET", "POST"])
def promotion_edit_form(code):
    item = promotion_repository.find_by_code(code)
    if not item: abort(404)
    if request.method == "POST":
        try: promotion_service.update(code, promotion_form_data(request.form, code)); flash("Đã cập nhật khuyến mãi", "success"); return redirect(url_for("web.promotion_detail", code=code))
        except (ValidationError, ValueError) as error: flash(str(error), "danger")
    return render_template("promotions/form.html", item=item)


@bp.get("/khuyen-mai/<code>")
def promotion_detail(code):
    item = promotion_repository.find_by_code(code)
    if not item: abort(404)
    targets = list(get_db().products.find({"$or": [{"productCode": {"$in": item.get("targets", {}).get("productCodes", [])}}, {"category.categoryCode": {"$in": item.get("targets", {}).get("categories", [])}}]}))
    usage = list(get_db().orders.aggregate([{"$match": {"appliedPromotion.promoCode": code}}, {"$group": {"_id": None, "count": {"$sum": 1}, "discount": {"$sum": "$appliedPromotion.discountAmount"}}}]))
    return render_template("promotions/detail.html", item=item, targets=targets, usage=usage[0] if usage else {"count": 0, "discount": 0})


@bp.get("/khach-hang")
def customers(): return render_template("customers/list.html", rows=customer_repository.find_customers(request.args))


def customer_form_data(form, code=None):
    return {"customerCode": code or form.get("customerCode"), "fullName": form.get("fullName"), "email": form.get("email"), "address": form.get("address"), "level": form.get("level"), "joinedAt": form.get("joinedAt") or datetime.now(), "status": form.get("status")}


@bp.route("/khach-hang/them", methods=["GET", "POST"])
def customer_create_form():
    if request.method == "POST":
        try: customer_service.create(customer_form_data(request.form)); flash("Đã thêm khách hàng", "success"); return redirect(url_for("web.customers"))
        except ValidationError as error: flash(str(error), "danger")
    return render_template("customers/form.html", item=None)


@bp.route("/khach-hang/<code>/sua", methods=["GET", "POST"])
def customer_edit_form(code):
    item = customer_repository.find_by_code(code)
    if not item: abort(404)
    if request.method == "POST":
        try: customer_service.update(code, customer_form_data(request.form, code)); flash("Đã cập nhật khách hàng", "success"); return redirect(url_for("web.customer_detail", code=code))
        except ValidationError as error: flash(str(error), "danger")
    return render_template("customers/form.html", item=item)


@bp.get("/khach-hang/<code>")
def customer_detail(code):
    item = customer_repository.find_by_code(code)
    if not item: abort(404)
    orders = order_service.list_orders({"customerCode": code})
    reviews = review_repository.find_reviews({"customerCode": code})
    return render_template("customers/detail.html", item=item, orders=orders, reviews=reviews)


@bp.get("/danh-gia")
def reviews(): return render_template("reviews/list.html", rows=review_repository.find_reviews(request.args))


@bp.post("/danh-gia")
def create_review():
    try:
        data = request.form.to_dict(); data["images"] = [x.strip() for x in data.get("images", "").splitlines() if x.strip()]
        data.pop('csrf_token', None)
        review_service.create_own(g.current_user, data); flash("Đã gửi đánh giá và đang chờ duyệt", "success")
    except ValidationError as error: flash(str(error), "danger")
    return redirect(url_for("auth.own_reviews"))


@bp.post("/danh-gia/<code>/trang-thai")
def review_status(code):
    try: review_service.moderate(g.current_user, code, request.form.get("status")); flash("Đã cập nhật đánh giá", "success")
    except (ValidationError, LookupError) as error: flash(str(error), "danger")
    return redirect(url_for("web.reviews"))


@bp.get("/don-hang")
def orders(): return render_template("orders/list.html", rows=order_service.list_orders(request.args))


@bp.get("/don-hang/<code>")
def order_detail(code):
    item = order_service.get_order(code)
    if not item: abort(404)
    subtotal = sum(row["quantity"] * row["unitPrice"] for row in item["items"])
    return render_template("orders/detail.html", item=item, subtotal=subtotal)


@bp.get("/thong-ke")
def dashboard(): return render_template("dashboard/index.html")


@bp.get("/bao-cao")
def query_demo():
    selected = request.args.get("report", "NC05")
    if selected not in REPORTS:
        abort(400)
    rows = serialize(report_repository.run_basic(selected))
    for row in rows:
        if selected == "NC08":
            row["monthLabel"] = f"{int(row.get('month', 0)):02d}/{row.get('year', '')}"
    groups = {}
    for code, info in REPORTS.items():
        if not has_permission(g.current_user, REPORT_PERMISSIONS[code]):
            continue
        groups.setdefault(info["group"], []).append((code, info))
    return render_template("queries.html", groups=groups, selected=selected, report=REPORTS[selected], rows=rows, cell=_report_cell)



