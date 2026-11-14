"""Bổ sung dữ liệu giao dịch giả lập; chỉ ghi khi các collection đích còn trống."""
from datetime import datetime, timedelta
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pymongo import MongoClient
from config import Config
from services.promotion_pricing import calculate
from services.shopping_common import ShoppingError


def main():
    if Config.MONGO_DB != 'promotion_review_management':
        raise RuntimeError('Dừng: database không phải promotion_review_management')
    db = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=10000)[Config.MONGO_DB]
    names = ('customers', 'orders', 'reviews')
    if any(db[name].count_documents({}) for name in names):
        raise RuntimeError('Dừng: customers, orders hoặc reviews đã có dữ liệu')
    products = list(db.products.find({'status': 'active'}).sort('productCode', 1))
    promotions = list(db.promotions.find({'status': 'active'}).sort('promoCode', 1))
    if len(products) < 20 or not promotions:
        raise RuntimeError('Cần ít nhất 20 sản phẩm và một khuyến mãi hoạt động')
    rng = random.Random(20261114)
    now = datetime.utcnow().replace(microsecond=0)
    people = ['Nguyễn Minh Anh', 'Trần Thu Hà', 'Lê Quốc Bảo', 'Phạm Ngọc Lan', 'Võ Thanh Tùng',
              'Đỗ Mỹ Linh', 'Bùi Gia Huy', 'Huỳnh Khánh Vy', 'Ngô Hoàng Nam', 'Đặng Thảo Nhi',
              'Phan Quốc Hưng', 'Đinh Phương Thảo', 'Vũ Đức Long', 'Hồ Ngọc Mai', 'Dương Khánh An',
              'Trương Bảo Trân', 'Lý Thành Đạt', 'Nguyễn Hoài Phương', 'Trần Gia Bảo', 'Lê Minh Châu']
    addresses = ['Quận 1, TP. Hồ Chí Minh', 'Thủ Đức, TP. Hồ Chí Minh', 'Hải Châu, Đà Nẵng',
                 'Cầu Giấy, Hà Nội', 'Ninh Kiều, Cần Thơ']
    customers = [{'customerCode': f'DEMOKH{i:04}', 'fullName': name,
                  'email': f'khachhang{i:02}@example.test', 'phone': f'090800{i:04}',
                  'address': addresses[(i - 1) % len(addresses)], 'level': ('normal', 'silver', 'gold')[i % 3],
                  'joinedAt': now - timedelta(days=180 + i), 'status': 'active', 'demoData': True}
                 for i, name in enumerate(people, 1)]
    orders, reviews = [], []
    texts = ['Sản phẩm đúng mô tả, đóng gói cẩn thận.', 'Sử dụng ổn định, giao hàng đúng hẹn.',
             'Chất lượng tốt, phù hợp nhu cầu sử dụng hằng ngày.', 'Thiết kế đẹp, cần thêm thời gian trải nghiệm.',
             'Dùng tốt nhưng thời gian giao hàng hơi lâu.']
    for i in range(60):
        customer = customers[i % len(customers)]
        product = products[(i * 7) % len(products)]
        quantity = 1 if i % 6 else 2
        subtotal = int(product['price']) * quantity
        # Đơn giả lập là đơn lịch sử: không sửa tồn kho và không tạo marker đặt giữ.
        order_date = now - timedelta(days=(i * 3) % 165 + 1)
        status = ('completed', 'completed', 'confirmed', 'pending', 'cancelled')[i % 5]
        lines = [{'productCode': product['productCode'], 'productName': product['name'],
                  'quantity': quantity, 'unitPrice': int(product['price'])}]
        eligible_lines = [{**lines[0], 'lineTotal': subtotal,
                           'categoryCode': product.get('category', {}).get('categoryCode', '')}]
        applied = None
        if i % 2 == 0:
            for promo in promotions:
                if promo.get('startDate') <= order_date <= promo.get('endDate'):
                    try:
                        discount = calculate(promo, eligible_lines, subtotal, now=order_date)
                    except (ShoppingError, TypeError, ValueError):
                        continue
                    if discount:
                        applied = {'promoCode': promo['promoCode'], 'discountAmount': int(discount)}
                        break
        order = {'orderCode': f'DEMODH{i + 1:05}', 'customerCode': customer['customerCode'],
                 'orderDate': order_date, 'items': lines, 'appliedPromotion': applied,
                 'subtotal': subtotal, 'shippingFee': 0, 'totalAmount': subtotal - (applied or {}).get('discountAmount', 0),
                 'status': status, 'paymentMethod': 'COD', 'demoData': True}
        orders.append(order)
        if status in ('confirmed', 'completed') and len(reviews) < 36:
            reviews.append({'reviewCode': f'DEMODG{len(reviews) + 1:05}', 'productCode': product['productCode'],
                            'productName': product['name'], 'productImage': product.get('image'),
                            'customer': {'customerCode': customer['customerCode'], 'customerName': customer['fullName']},
                            'orderCode': order['orderCode'], 'rating': (5, 4, 5, 3, 4)[i % 5],
                            'title': 'Trải nghiệm sản phẩm', 'content': texts[i % len(texts)], 'images': [],
                            'verifiedPurchase': True, 'helpfulCount': i % 8,
                            'status': 'pending' if i % 9 == 0 else 'approved',
                            'createdAt': order_date + timedelta(hours=12), 'demoData': True})
    for name, rows in [('customers', customers), ('orders', orders), ('reviews', reviews)]:
        result = db[name].insert_many(rows, ordered=True)
        print(f'{name}: thêm {len(result.inserted_ids)}')


if __name__ == '__main__':
    main()
