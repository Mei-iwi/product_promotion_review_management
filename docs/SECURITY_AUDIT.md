# Audit trước triển khai

Baseline commit: `6f88d79bfadcb797df90b4a5d605c862e7287710`. Working tree sạch.
Đã đọc app/config, routes, services, repositories, db, templates, static JS/CSS,
scripts, tests, README, schema và cả hai Compose. Không có AGENTS.md trong dự án.

| Nhóm route hiện tại | Methods | Dữ liệu / thay đổi | Hiện trạng |
|---|---|---|---|
| `/`, `/thong-ke`, `/bao-cao` | GET | Tổng hợp, báo cáo có PII | Anonymous |
| `/san-pham`, `/san-pham/<code>` | GET | Sản phẩm nội bộ, đánh giá, khuyến mãi | Anonymous |
| `/san-pham/them`, `/san-pham/<code>/sua` | GET, POST | Tạo/sửa sản phẩm | Anonymous, không CSRF |
| `/khuyen-mai`, `/khuyen-mai/<code>` | GET | Chương trình, thống kê sử dụng | Anonymous |
| `/khuyen-mai/them`, `/khuyen-mai/<code>/sua` | GET, POST | Tạo/sửa chương trình | Anonymous, không CSRF |
| `/khach-hang`, `/khach-hang/<code>` | GET | PII, đơn hàng, đánh giá | Anonymous |
| `/khach-hang/them`, `/khach-hang/<code>/sua` | GET, POST | Tạo/sửa hồ sơ | Anonymous, mass assignment API |
| `/danh-gia` | GET, POST | Xem toàn bộ / tạo với mã khách client gửi | Anonymous |
| `/danh-gia/<code>/trang-thai` | POST | Duyệt/từ chối | Anonymous |
| `/don-hang`, `/don-hang/<code>` | GET | Đơn hàng chi tiết | Anonymous |
| `/api/products`, `/api/products/<code>` | GET; POST collection; PUT, DELETE detail | CRUD; DELETE lọc createdByApp | Anonymous |
| `/api/products/<code>/status`, `.../tags` | PATCH | Trạng thái, tags | Anonymous |
| `/api/promotions`, `/api/promotions/<code>` | GET; POST collection; PUT detail | CRU khuyến mãi | Anonymous |
| `/api/customers`, `/api/customers/<code>` | GET; POST collection; PUT detail | CRU hồ sơ | Anonymous |
| `/api/reviews`, `/api/reviews/<code>/status` | GET, POST; PATCH status | Danh sách, tạo, duyệt | Anonymous |
| `/api/orders`, `/api/orders/<code>` | GET | Đơn hàng | Anonymous |
| `/api/dashboard/{summary,ratings,promotions,sales}` | GET | ratings có NC10, sales có NC04 (PII) | Anonymous |
| `/static/<path>` | GET | CSS/JS/SVG | Công khai |

HEAD theo GET, OPTIONS tự động. Chưa có users, sessions, audit, hashing hay authorization.
Form Jinja gửi POST; JS dashboard/report dùng GET fetch; app.js chỉ chặn double submit.
Config có SECRET_KEY fallback yếu; cookie session Flask mặc định; chưa có headers/size limit.

## Collections và quan hệ

- products: unique productCode; category embedded, tags/attributes; CRUD giữ nguyên.
- promotions: unique promoCode; conditions/targets embedded; kiểm tra ngày, giá trị, trạng thái.
- customers: unique customerCode/email; level/joinedAt/status. Đây là hồ sơ, không phải tài khoản.
- orders: customerCode → customers, items.productCode → products, appliedPromotion → promotions;
  chỉ đọc, lọc theo customer/status/product/date/promotion; xác minh mua qua confirmed/completed.
- reviews: unique reviewCode; productCode và customer snapshot; tạo pending, tính verifiedPurchase từ orders.
- Index hiện hữu được mô tả trong db/indexes.py; ứng dụng chỉ inspect, không tạo lại dữ liệu.
- CB01–07, CB10: sản phẩm, không PII. CB08/12: review chi tiết, nhạy cảm.
  CB09/11: đơn hàng chi tiết, nhạy cảm. NC04/10: định danh khách hàng, nhạy cảm.
  NC01/02/03/05/06/07/08/09: tổng hợp không định danh, cho phép ANALYST.

## Baseline

Python hệ thống và .venv hiện tại thiếu pytest; .venv còn trỏ tới Python 3.12 không tồn tại.
Tạo môi trường kiểm thử riêng `.venv-security` để không ghi đè môi trường của người dùng.
Kết quả baseline được ghi bổ sung sau khi dependency sẵn sàng.

Baseline trong `.venv-security`: **25 passed in 0.43s** (Pytest + Mongomock).

Theo yêu cầu tiếp theo của người dùng, môi trường kiểm thử đã được hợp nhất vào
`.venv` (Python 3.13). `.venv-security` đã được dọn sau khi cài dependency và kiểm tra
ứng dụng trong `.venv`; các tên môi trường ở phần baseline phía trên là ghi nhận lịch sử.
