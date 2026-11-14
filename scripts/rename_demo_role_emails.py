"""Đổi email đăng nhập các tài khoản mẫu, không sửa mật khẩu hay vai trò."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pymongo import MongoClient
from config import Config


def main():
    if Config.MONGO_DB != 'promotion_review_management':
        raise SystemExit('Database không đúng; dừng.')
    db = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=10000)[Config.MONGO_DB]
    accounts = [('quanlytaikhoan', 'ACCOUNT_MANAGER'), ('sanpham', 'PRODUCT_STAFF'),
                ('khuyenmai', 'MARKETING_STAFF'), ('hotro', 'SUPPORT_STAFF'),
                ('kiemdanhgia', 'REVIEW_MODERATOR'), ('phantich', 'ANALYST'),
                ('khachhang', 'CUSTOMER')]
    for name, role in accounts:
        old, new = name + '@example.test', name + '@gmail.com'
        if db.users.find_one({'emailNormalized': new}):
            raise SystemExit(f'Email đích {new} đã tồn tại; không thay đổi.')
        if not db.users.find_one({'emailNormalized': old, 'role': role}):
            raise SystemExit(f'Không tìm thấy tài khoản nguồn {old} với vai trò {role}.')
    for name, role in accounts:
        old, new = name + '@example.test', name + '@gmail.com'
        result = db.users.update_one({'emailNormalized': old, 'role': role},
                                     {'$set': {'email': new, 'emailNormalized': new}})
        if result.modified_count != 1:
            raise RuntimeError(f'Không cập nhật được {old}; kiểm tra các tài khoản đã đổi.')
        print(f'{role}: {new}')


if __name__ == '__main__':
    main()
