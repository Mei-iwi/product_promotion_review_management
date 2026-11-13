"""Synthetic fixtures shared by the opt-in replica tests and browser verifier."""
import secrets
from datetime import timedelta
from app import create_app
from repositories.security_repository import utcnow
from repositories import shopping_repository
from services import auth_service


def seeded_app(client, database):
    app = create_app({'TESTING': True, 'APP_ENV': 'development', 'CHECKOUT_ENABLED': True,
                      'AUTH_COOKIE_NAME': 'dev-auth', 'AUTH_COOKIE_SECURE': False,
                      'SESSION_COOKIE_SECURE': False, 'SECRET_KEY': secrets.token_hex(32), 'MONGO_DB': database}, client)
    with app.app_context():
        db = app.extensions['mongo_db']
        now = utcnow()
        db.products.insert_many([
            {'productCode': 'P1', 'name': 'Tai nghe Sony WH-1000XM5', 'brand': 'Sony', 'price': 500000, 'stock': 10, 'status': 'active', 'category': {'categoryCode': 'AUDIO', 'categoryName': 'Âm thanh'}, 'attributes': {'color': 'Đen'}},
            {'productCode': 'P2', 'name': 'Chuột Logitech MX Master 3S', 'brand': 'Logitech', 'price': 300000, 'stock': 10, 'status': 'active', 'category': {'categoryCode': 'MOUSE', 'categoryName': 'Chuột'}, 'attributes': {}},
        ])
        db.promotions.insert_one({'promoCode': 'DEMO10', 'name': 'Ưu đãi demo', 'promoType': 'percentage', 'value': 10,
                                  'status': 'active', 'startDate': now - timedelta(days=1), 'endDate': now + timedelta(days=30),
                                  'conditions': {'minOrderValue': 0, 'maxDiscount': 40000},
                                  'targets': {'productCodes': ['P1'], 'categories': ['AUDIO']}, 'usageLimit': 0})
        for code in ['C1', 'C2']:
            db.customers.insert_one({'customerCode': code, 'fullName': 'Khách hàng demo ' + code,
                                     'email': code.lower() + '@example.test', 'address': '12 Đường Demo, Quận 1', 'status': 'active', 'level': 'normal'})
        password = 'replica phrase ' + secrets.token_hex(24)
        admin = auth_service.create_user({'email': 'admin@example.test', 'password': password, 'role': 'ADMIN'}, bootstrap=True)
        customers = [auth_service.create_user({'email': code.lower() + '@example.test', 'password': password, 'role': 'CUSTOMER', 'customerCode': code}, admin) for code in ['C1', 'C2']]
        shopping_repository.reconcile()
    return app, admin, customers, password
