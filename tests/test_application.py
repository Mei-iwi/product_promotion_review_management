from db.mongo import get_db
from repositories import report_repository
from services import product_service, promotion_service, customer_service, review_service
from services.helpers import ValidationError
import pytest


def product_payload(code="SANPHAM2026100001"):
    return {"productCode": code, "name": "Hub USB-C 6 trong 1", "category": {"categoryCode": "DM-PHUKIEN", "categoryName": "Phụ kiện"}, "brand": "UGREEN", "price": 890000, "stock": 25, "attributes": {"ports": 6}, "tags": ["USB-C"], "status": "active"}


def test_01_mongo_connection(app): assert get_db().name == "QL_KHUYENMAI_DANHGIA_TEST"
def test_02_product_list(app): assert product_service.list_products()[1] == 2
def test_03_product_category_filter(app): assert product_service.list_products({"category": "DM-PHUKIEN"})[1] == 1
def test_04_product_price_filter(app): assert product_service.list_products({"min_price": 5000000, "max_price": 6000000})[0][0]["productCode"].endswith("0007")


def test_05_product_create_validation(app):
    data = product_payload(); data["price"] = -1
    with pytest.raises(ValidationError): product_service.create(data)


def test_06_product_update(app):
    data = product_payload("SANPHAM2026090007"); data["price"] = 5000000
    assert product_service.update(data["productCode"], data)["price"] == 5000000


def test_07_duplicate_product_code(app):
    with pytest.raises(ValidationError): product_service.create(product_payload("SANPHAM2026090007"))


def test_08_promotion_date_validation(app):
    data = {"promoCode": "KHUYENMAI2026100001", "name": "Sai ngày", "promoType": "percentage", "value": 10, "startDate": "2026-10-10", "endDate": "2026-10-01", "status": "active"}
    with pytest.raises(ValidationError): promotion_service.create(data)


def test_09_customer_duplicate_email(app):
    data = {"customerCode": "KHACHHANG20260003", "fullName": "Lê Quốc Bảo", "email": "anh@qlkm.local", "level": "normal", "status": "active"}
    with pytest.raises(ValidationError): customer_service.create(data)


def test_10_review_rating_invalid(app):
    with pytest.raises(ValidationError): review_service.create({"reviewCode": "DANHGIA2026100001", "productCode": "SANPHAM2026090007", "customerCode": "KHACHHANG20260001", "rating": 6, "content": "Không hợp lệ"})


def test_11_create_review_valid(app):
    row = review_service.create({"reviewCode": "DANHGIA2026100001", "productCode": "SANPHAM2026090007", "customerCode": "KHACHHANG20260001", "rating": 4, "content": "Sử dụng ổn định"})
    assert row["status"] == "pending"


def test_12_verified_purchase(app):
    row = review_service.create({"reviewCode": "DANHGIA2026100002", "productCode": "SANPHAM2026090007", "customerCode": "KHACHHANG20260001", "rating": 4, "content": "Đã mua"})
    assert row["verifiedPurchase"] is True


def test_13_review_approve_reject(app):
    assert review_service.set_status("DANHGIA2026090001", "rejected")["status"] == "rejected"
    assert review_service.set_status("DANHGIA2026090001", "approved")["status"] == "approved"


def test_14_dashboard_nc01(app): assert report_repository.nc01()[0]["avgRating"] == 5
def test_15_dashboard_nc05(app): assert report_repository.nc05()[0]["quantitySold"] == 2
def test_16_dashboard_nc07(app): assert report_repository.nc07()[0]["totalDiscount"] == 300000
def test_17_lookup_nc09(app): assert report_repository.nc09()[0]["productName"] == "AirPods Pro thế hệ 2"
def test_18_route_404(client): assert client.get("/api/products/KHONGCO").status_code == 404


def test_19_api_envelope(client):
    body = client.get("/api/products").get_json()
    assert set(body) == {"success", "message", "data"} and body["success"] is True


def test_20_empty_collections_do_not_crash(app):
    for name in ("products", "promotions", "customers", "reviews", "orders"): get_db()[name].delete_many({})
    assert report_repository.summary()["revenue"] == 0 and report_repository.nc01() == []


def test_21_dashboard_uses_semantic_fields(app):
    assert "rating" in report_repository.nc03()[0]
    assert "promoCode" in report_repository.nc07()[0]
    assert {"year", "month"} <= report_repository.nc08()[0].keys()


def test_22_dashboard_page_loads_offline_svg_script(client):
    html = client.get("/thong-ke").get_data(as_text=True)
    assert html.count("svg-chart-host") == 5
    assert "dashboard.js?v=5" in html
    assert "chart.js" not in html


def test_23_business_report_renders_as_table(client):
    html = client.get("/bao-cao?report=NC05").get_data(as_text=True)
    assert "Báo cáo nghiệp vụ" in html
    assert "Doanh thu theo sản phẩm" in html
    assert "AirPods Pro thế hệ 2" in html
    assert "<table" in html
    assert "query-result" not in html
    assert "reports.js?v=1" in html


def test_24_navigation_has_no_index_numbers(client):
    html = client.get("/").get_data(as_text=True)
    assert "nav-index" not in html
    assert ">Báo cáo</a>" in html


def test_25_deep_pages_have_back_button(client):
    paths = [
        "/san-pham/them",
        "/san-pham/SANPHAM2026090007",
        "/san-pham/SANPHAM2026090007/sua",
        "/khuyen-mai/them",
        "/khuyen-mai/KHUYENMAI2026090001",
        "/khuyen-mai/KHUYENMAI2026090001/sua",
        "/khach-hang/them",
        "/khach-hang/KHACHHANG20260001",
        "/khach-hang/KHACHHANG20260001/sua",
        "/don-hang/DONHANG2026090001",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert "Quay lại" in response.get_data(as_text=True)

