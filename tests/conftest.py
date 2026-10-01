from datetime import datetime
from pathlib import Path
import sys
import mongomock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app


@pytest.fixture()
def app():
    mongo = mongomock.MongoClient()
    app = create_app({"TESTING": True, "MONGO_DB": "QL_KHUYENMAI_DANHGIA_TEST", "SECRET_KEY": "test"}, mongo)
    db = app.extensions["mongo_db"]
    db.products.create_index("productCode", unique=True)
    db.customers.create_index("customerCode", unique=True)
    db.customers.create_index("email", unique=True)
    db.promotions.create_index("promoCode", unique=True)
    db.reviews.create_index("reviewCode", unique=True)
    db.products.insert_many([
        {"productCode": "SANPHAM2026090001", "name": "iPhone 15 Pro Max 256GB", "category": {"categoryCode": "DM-DIENTHOAI", "categoryName": "Điện thoại"}, "brand": "Apple", "price": 33990000, "stock": 18, "attributes": {"storage": "256GB"}, "tags": ["cao cấp"], "status": "active"},
        {"productCode": "SANPHAM2026090007", "name": "AirPods Pro thế hệ 2", "category": {"categoryCode": "DM-PHUKIEN", "categoryName": "Phụ kiện"}, "brand": "Apple", "price": 5490000, "stock": 40, "attributes": {}, "tags": ["văn phòng"], "status": "active"},
    ])
    db.customers.insert_many([
        {"customerCode": "KHACHHANG20260001", "fullName": "Nguyễn Minh Anh", "email": "anh@qlkm.local", "address": "Quận 7", "level": "gold", "joinedAt": datetime(2026, 1, 10), "status": "active"},
        {"customerCode": "KHACHHANG20260002", "fullName": "Trần Thu Hà", "email": "ha@qlkm.local", "address": "Thủ Đức", "level": "silver", "joinedAt": datetime(2026, 1, 22), "status": "active"},
    ])
    db.promotions.insert_one({"promoCode": "KHUYENMAI2026090001", "name": "Ưu đãi phụ kiện", "promoType": "percentage", "value": 10, "startDate": datetime(2026, 9, 1), "endDate": datetime(2026, 9, 30), "conditions": {"minOrderValue": 500000, "maxDiscount": 300000}, "targets": {"productCodes": ["SANPHAM2026090007"], "categories": ["DM-PHUKIEN"]}, "usageLimit": 600, "status": "active"})
    db.orders.insert_one({"orderCode": "DONHANG2026090001", "customerCode": "KHACHHANG20260001", "orderDate": datetime(2026, 9, 20), "items": [{"productCode": "SANPHAM2026090007", "productName": "AirPods Pro thế hệ 2", "quantity": 2, "unitPrice": 5490000}], "appliedPromotion": {"promoCode": "KHUYENMAI2026090001", "discountAmount": 300000}, "totalAmount": 10680000, "status": "completed"})
    db.reviews.insert_one({"reviewCode": "DANHGIA2026090001", "productCode": "SANPHAM2026090007", "customer": {"customerCode": "KHACHHANG20260001", "customerName": "Nguyễn Minh Anh"}, "rating": 5, "title": "Tốt", "content": "Âm thanh rõ", "images": [], "verifiedPurchase": True, "helpfulCount": 1, "status": "approved", "createdAt": datetime(2026, 9, 21)})
    yield app


@pytest.fixture()
def client(app): return app.test_client()

