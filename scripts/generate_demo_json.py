"""Generate import-only demo JSON files; never connect to or modify MongoDB."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'demo'

# Real product model names; prices, stock and promotions are fictional retail data.
CATALOG = [
    ('DM-DIENTHOAI', 'Điện thoại', [
        ('iPhone 15 128GB', 'Apple', 16990000),
        ('Samsung Galaxy S24 Ultra', 'Samsung', 26990000),
        ('Xiaomi Redmi Note 13 Pro', 'Xiaomi', 6990000),
        ('OPPO Reno11 5G', 'OPPO', 8990000),
        ('realme 11 5G', 'realme', 5490000),
    ]),
    ('DM-LAPTOP', 'Laptop', [
        ('MacBook Air 13 inch M2', 'Apple', 21990000),
        ('Dell Inspiron 15 3530', 'Dell', 15490000),
        ('ASUS Vivobook 15 X1504VA', 'ASUS', 13990000),
        ('Lenovo IdeaPad Slim 3 15IRH8', 'Lenovo', 14990000),
        ('HP Pavilion 15-eg', 'HP', 16990000),
    ]),
    ('DM-MAYTINHBANG', 'Máy tính bảng', [
        ('iPad Gen 10 Wi-Fi 64GB', 'Apple', 8990000),
        ('Samsung Galaxy Tab S9 FE', 'Samsung', 9990000),
        ('Xiaomi Pad 6', 'Xiaomi', 7490000),
        ('Lenovo Tab M11', 'Lenovo', 4990000),
        ('OPPO Pad Air', 'OPPO', 4490000),
    ]),
    ('DM-TAINGHE', 'Tai nghe', [
        ('AirPods Pro thế hệ 2 USB-C', 'Apple', 5490000),
        ('Sony WH-1000XM5', 'Sony', 7490000),
        ('Samsung Galaxy Buds2 Pro', 'Samsung', 2990000),
        ('JBL Tune 520BT', 'JBL', 1090000),
        ('Anker Soundcore Liberty 4 NC', 'Anker', 2190000),
    ]),
    ('DM-LOA', 'Loa', [
        ('JBL Flip 6', 'JBL', 2490000),
        ('Sony SRS-XB100', 'Sony', 990000),
        ('Marshall Emberton II', 'Marshall', 3990000),
        ('Anker Soundcore Motion+', 'Anker', 1990000),
        ('Logitech Z407', 'Logitech', 2290000),
    ]),
    ('DM-DONGHO', 'Đồng hồ thông minh', [
        ('Apple Watch SE 2022 GPS 40mm', 'Apple', 5490000),
        ('Samsung Galaxy Watch6 40mm', 'Samsung', 4990000),
        ('Huawei Watch Fit 3', 'Huawei', 2790000),
        ('Garmin Forerunner 165', 'Garmin', 6690000),
        ('Xiaomi Smart Band 8', 'Xiaomi', 790000),
    ]),
    ('DM-MANHINH', 'Màn hình', [
        ('Dell UltraSharp U2422H', 'Dell', 4790000),
        ('LG UltraGear 24GN60R-B', 'LG', 3290000),
        ('ASUS TUF Gaming VG249Q1A', 'ASUS', 3490000),
        ('Samsung Odyssey G5 LC27G55T', 'Samsung', 5290000),
        ('BenQ GW2480', 'BenQ', 2590000),
    ]),
    ('DM-BANPHIM', 'Bàn phím', [
        ('Logitech MX Keys S', 'Logitech', 2490000),
        ('Keychron K2 V2', 'Keychron', 1990000),
        ('Razer BlackWidow V3', 'Razer', 2290000),
        ('ASUS ROG Strix Scope II', 'ASUS', 2990000),
        ('Akko 5075B Plus', 'Akko', 1790000),
    ]),
    ('DM-CHUOT', 'Chuột máy tính', [
        ('Logitech MX Master 3S', 'Logitech', 2190000),
        ('Razer DeathAdder V3', 'Razer', 1390000),
        ('Logitech G304 LIGHTSPEED', 'Logitech', 690000),
        ('SteelSeries Rival 3', 'SteelSeries', 590000),
        ('Microsoft Bluetooth Mouse', 'Microsoft', 490000),
    ]),
    ('DM-PHUKIEN', 'Phụ kiện', [
        ('Anker Nano II 65W A2663', 'Anker', 790000),
        ('UGREEN Nexode 65W CD244', 'UGREEN', 690000),
        ('Samsung Battery Pack 10000mAh EB-P3400', 'Samsung', 790000),
        ('Apple USB-C to USB-C Charge Cable 1m', 'Apple', 490000),
        ('Kingston DataTraveler Exodia 128GB', 'Kingston', 199000),
    ]),
]


def generate_products():
    products = []
    for category_code, category_name, rows in CATALOG:
        for name, brand, price in rows:
            index = len(products) + 1
            products.append({
                'productCode': f'SANPHAM202611{index:04}',
                'name': name,
                'category': {'categoryCode': category_code, 'categoryName': category_name},
                'brand': brand,
                'price': price,
                'stock': 8 + (index * 7) % 73,
                # These are demo-store merchandising fields, not manufacturer specs.
                'attributes': {'condition': 'Mới', 'salesChannel': 'Online và cửa hàng'},
                'tags': ['demo-202611', category_name.lower(), 'văn phòng' if category_code in {'DM-LAPTOP', 'DM-MANHINH', 'DM-BANPHIM', 'DM-CHUOT'} else 'công nghệ'],
                'status': 'active',
            })
    manifest = OUTPUT / 'product-images.json'
    if manifest.exists():
        images = {row['productCode']: row['image'] for row in json.loads(manifest.read_text(encoding='utf-8'))}
        for product in products:
            if product['productCode'] in images:
                product['image'] = images[product['productCode']]
    return products


def date(value):
    # Extended JSON: Compass/mongoimport creates a BSON Date, not a string.
    return {'$date': value}


def generate_promotions(products):
    promotions = []

    def add(name, kind, value, minimum, maximum, limit, product_codes=None, categories=None,
            start='2026-11-01T00:00:00.000Z', end='2027-01-31T23:59:59.999Z', status='active'):
        index = len(promotions) + 1
        promotions.append({
            'promoCode': f'KHUYENMAI202611{index:04}',
            'name': name,
            'promoType': kind,
            'value': value,
            'startDate': date(start),
            'endDate': date(end),
            'conditions': {'minOrderValue': minimum, 'maxDiscount': maximum},
            'targets': {'productCodes': product_codes or [], 'categories': categories or []},
            'usageLimit': limit,
            'status': status,
        })

    offers = [
        ('Ưu đãi điện thoại tháng 11 - giảm 5%', 5, 5000000, 1000000, 200),
        ('Laptop học tập và làm việc - giảm 7%', 7, 10000000, 1500000, 150),
        ('Máy tính bảng cho học tập - giảm 8%', 8, 4000000, 800000, 180),
        ('Tai nghe yêu thích - giảm 10%', 10, 1000000, 500000, 300),
        ('Âm thanh cuối tuần - giảm 10%', 10, 900000, 400000, 250),
        ('Đồng hồ đồng hành - giảm 8%', 8, 700000, 500000, 200),
        ('Nâng cấp góc làm việc - giảm 10%', 10, 2500000, 600000, 160),
        ('Bàn phím mới, trải nghiệm mới - giảm 12%', 12, 1500000, 400000, 220),
        ('Chuột máy tính - giảm 15%', 15, 450000, 300000, 350),
        ('Phụ kiện thiết yếu - giảm 10%', 10, 190000, 100000, 500),
    ]
    for category, offer in zip(CATALOG, offers):
        name, value, minimum, maximum, limit = offer
        add(name, 'percentage', value, minimum, maximum, limit, categories=[category[0]])

    # Fixed-value vouchers for actual products present in products.json.
    fixed = [
        (0, 'Voucher iPhone 15 - giảm 500.000đ', 500000, 15000000, 80),
        (5, 'Voucher MacBook Air M2 - giảm 1.000.000đ', 1000000, 20000000, 60),
        (15, 'Voucher AirPods Pro 2 - giảm 300.000đ', 300000, 5000000, 120),
        (20, 'Voucher JBL Flip 6 - giảm 200.000đ', 200000, 2000000, 100),
        (35, 'Voucher Logitech MX Keys S - giảm 200.000đ', 200000, 2000000, 100),
        (40, 'Voucher Logitech MX Master 3S - giảm 150.000đ', 150000, 2000000, 120),
    ]
    for product_index, name, value, minimum, limit in fixed:
        add(name, 'fixed', value, minimum, value, limit, product_codes=[products[product_index]['productCode']])

    all_categories = [category[0] for category in CATALOG]
    add('Ngày đôi 11.11 - giảm 11%', 'percentage', 11, 500000, 500000, 1111,
        categories=all_categories, start='2026-11-10T00:00:00.000Z', end='2026-11-12T23:59:59.999Z')
    add('Black Friday - giảm 15%', 'percentage', 15, 1000000, 1000000, 500,
        categories=all_categories, start='2026-11-20T00:00:00.000Z', end='2026-11-30T23:59:59.999Z')
    add('Ưu đãi phụ kiện tháng 10 - đã kết thúc', 'percentage', 10, 300000, 100000, 300,
        categories=['DM-PHUKIEN'], start='2026-10-01T00:00:00.000Z', end='2026-10-31T23:59:59.999Z', status='expired')
    add('Combo góc làm việc - tạm ngừng', 'fixed', 300000, 3000000, 300000, 100,
        categories=['DM-MANHINH', 'DM-BANPHIM', 'DM-CHUOT'], status='inactive')
    return promotions


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    products = generate_products()
    promotions = generate_promotions(products)
    assert len(products) == 50 and len(promotions) == 20
    for name, rows in [('products', products), ('promotions', promotions)]:
        (OUTPUT / f'{name}.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Generated data/demo/products.json: 50 products')
    print('Generated data/demo/promotions.json: 20 promotions')


if __name__ == '__main__':
    main()
