"""Tạo tài khoản thử nghiệm theo vai trò; mật khẩu được đọc từ biến môi trường."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding='utf-8')
from flask import Flask
from config import Config
from db.mongo import init_mongo
from services import auth_service


def main():
    password = os.environ.get('DEMO_ROLE_PASSWORD')
    if not password:
        raise SystemExit('Cần đặt biến DEMO_ROLE_PASSWORD.')
    app = Flask(__name__)
    app.config.from_object(Config)
    init_mongo(app)
    with app.app_context():
        db = app.extensions['mongo_db']
        if db.name != 'promotion_review_management':
            raise SystemExit('Database không đúng; dừng.')
        admin = db.users.find_one({'emailNormalized': 'admin123@gmail.com', 'role': 'ADMIN', 'status': 'active'})
        if not admin or not auth_service.verify(admin.get('passwordHash'), password):
            raise SystemExit('Không xác thực được tài khoản ADMIN.')
        accounts = [
            ('quanlytaikhoan@gmail.com', 'ACCOUNT_MANAGER'),
            ('sanpham@gmail.com', 'PRODUCT_STAFF'),
            ('khuyenmai@gmail.com', 'MARKETING_STAFF'),
            ('hotro@gmail.com', 'SUPPORT_STAFF'),
            ('kiemdanhgia@gmail.com', 'REVIEW_MODERATOR'),
            ('phantich@gmail.com', 'ANALYST'),
            ('khachhang@gmail.com', 'CUSTOMER'),
        ]
        for email, role in accounts:
            existing = db.users.find_one({'emailNormalized': email})
            if existing:
                print(f'{email}: đã tồn tại ({existing.get("role")}); không thay đổi')
                continue
            data = {'email': email, 'password': password, 'role': role, 'actorPassword': password}
            if role == 'CUSTOMER':
                customer = db.customers.find_one({'customerCode': 'DEMOKH0001', 'status': 'active'})
                if not customer or db.users.find_one({'customerCode': customer['customerCode']}):
                    print(f'{email}: không có hồ sơ khách hàng phù hợp; bỏ qua')
                    continue
                data['customerCode'] = customer['customerCode']
            user = auth_service.create_user(data, admin)
            print(f'{email}: đã tạo {user["role"]}')


if __name__ == '__main__':
    main()
