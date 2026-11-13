# Dữ liệu demo sản phẩm và khuyến mãi

- `products.json`: 50 sản phẩm có tên mẫu thực tế, 10 danh mục, tất cả active.
- `promotions.json`: 20 chương trình/voucher, gồm 18 active, 1 expired, 1 inactive.
- Tên mẫu thuộc các thương hiệu thực tế; giá VND, tồn kho, điều kiện và chương trình
  khuyến mãi là dữ liệu giả lập của cửa hàng, không phải báo giá hoặc ưu đãi của hãng.
- Mã sản phẩm: `SANPHAM2026110001` đến `SANPHAM2026110050`.
- Mã khuyến mãi: `KHUYENMAI2026110001` đến `KHUYENMAI2026110020`.
- Ngày là MongoDB Extended JSON `$date`, để MongoDB lưu BSON Date phục vụ bộ lọc thời gian.
  Phần lớn ưu đãi có hiệu lực 01/11/2026–31/01/2027; Black Friday bắt đầu 20/11/2026.
- Không chứa `_id`, tài khoản, mật khẩu hoặc dữ liệu khách hàng.
- Cả 50 sản phẩm đã có ảnh lưu tại `static/img/products/`; trường `image` dùng đường dẫn nội bộ.
  Nguồn ảnh và checksum nằm trong `product-images.json`. Ảnh dùng minh họa dữ liệu demo.
  `generate_demo_json.py` giữ đường dẫn ảnh khi tạo lại JSON.

Để tải lại ảnh: cài `requirements-dev.txt`, chạy `python scripts/download_product_images.py`.
Thêm `--apply-db` nếu muốn gắn lại ảnh vào đúng sản phẩm hiện có trên database cấu hình trong `.env`.
Lệnh chỉ cập nhật trường ảnh cho mã/tên khớp, không thay giá, tồn kho hoặc chèn sản phẩm.

## Import bằng MongoDB Compass

Web chung **http://127.0.0.1:5002** dùng MongoDB Docker **127.0.0.1:27018**,
database `QL_KHUYENMAI_DANHGIA`. Kết nối bằng credential trong `.env`, authSource đúng database
và directConnection=true. Không import sang MongoDB local 27017.

1. Mở database `QL_KHUYENMAI_DANHGIA`.
2. Tạo collection `products` nếu chưa có. Chọn **Add Data → Import JSON or CSV file**,
   chọn `products.json`, định dạng JSON và import.
3. Tạo collection `promotions` nếu chưa có; import `promotions.json` tương tự.
4. Kiểm tra `startDate`, `endDate` của khuyến mãi hiển thị kiểu **Date**, không phải String/Object.
5. Tải lại web, mở **Sản phẩm** và **Khuyến mãi** bằng tài khoản có quyền tương ứng.

Import file một lần; import lặp lại có thể trùng mã nếu database chưa có unique index.
Không chọn drop/delete collection; giữ nguyên users, sessions, customers và dữ liệu cũ.
Sản phẩm được import trực tiếp không được gắn `createdByApp`; quy tắc xóa sản phẩm hiện tại vẫn áp dụng.
Hai file này không tạo đơn hàng hay đánh giá, nên các báo cáo doanh thu/đánh giá vẫn trống cho tới khi có dữ liệu tương ứng.

## Import bằng mongoimport (nếu đã cài MongoDB Database Tools)

Chạy từ thư mục gốc dự án, dành cho MongoDB local cổng 27017:

```bash
mongoimport --uri="mongodb://127.0.0.1:27017" --db=QL_KHUYENMAI_DANHGIA --collection=products --file=data/demo/products.json --jsonArray --mode=upsert --upsertFields=productCode
mongoimport --uri="mongodb://127.0.0.1:27017" --db=QL_KHUYENMAI_DANHGIA --collection=promotions --file=data/demo/promotions.json --jsonArray --mode=upsert --upsertFields=promoCode
```

Upsert giúp chạy lại mà không thêm bản ghi trùng mã; nó cập nhật các document có cùng mã demo.
Với MongoDB Docker, dùng kết nối có credential và cổng 27018 trong Compass;
không đưa mật khẩu vào command line hoặc Git.

Có thể tạo lại cùng hai file bằng `python scripts/generate_demo_json.py`.
Script chỉ ghi file JSON, không kết nối hay ghi dữ liệu vào MongoDB.

Sau khi import, chạy `docker compose exec app python -m flask --app app:create_app reconcile-promotion-usage` trước khi đặt hàng.
