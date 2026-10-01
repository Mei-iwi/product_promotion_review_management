# Đối chiếu mô hình dữ liệu

| Collection | Field chính | Kiểu/mô hình | Route sử dụng | Validation chính |
|---|---|---|---|---|
| products | productCode, category, attributes, tags | category/attributes embedded, tags array | `/san-pham`, `/api/products` | mã duy nhất, giá/tồn kho không âm |
| promotions | conditions, targets | embedded và array | `/khuyen-mai`, `/api/promotions` | ngày, loại giảm, giá trị, giới hạn |
| customers | customerCode, email | document | `/khach-hang`, `/api/customers` | mã/email duy nhất, level/status |
| reviews | productCode, customer | reference logic + customer snapshot | `/danh-gia`, `/api/reviews` | rating 1–5, sản phẩm/khách tồn tại |
| orders | customerCode, items, appliedPromotion | reference logic + embedded snapshot | `/don-hang`, `/api/orders` | đọc đúng items/promotion hiện hữu |

