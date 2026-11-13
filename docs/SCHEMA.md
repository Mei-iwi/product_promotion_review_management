# Đối chiếu mô hình dữ liệu

Schema và indexes bổ sung cho `users`, `sessions`, `audit_logs`, `security_limits`,
`security_locks` được mô tả tại [SECURITY.md](SECURITY.md#schema-và-indexes-bổ-sung).
`customers` tiếp tục là hồ sơ nghiệp vụ, tách biệt với tài khoản đăng nhập `users`.

Khu mua sắm bổ sung `carts` (owner userId/customerCode, items, promoCode, version),
`checkout_quotes` (quote 15 phút, totals/fingerprint, TTL), `shopping_state`
(đối soát usage/epoch), `promotions.commerceUsed` và các snapshot/marker trên orders.
Orders giữ schema cũ, thêm recipient, paymentMethod=COD, subtotal/shippingFee, statusHistory,
checkoutKey/requestHash và marker giữ tồn/lượt. Unique partial `(customerCode, checkoutKey)`
chặn đơn trùng; marker tách legacy khỏi đơn mới. Không có migration xóa dữ liệu.
Chi tiết transaction, đối soát, schema và cách chuyển sang replica set:
[SHOPPING.md](SHOPPING.md#dữ-liệu-và-nhất-quán).

| Collection | Field chính | Kiểu/mô hình | Route sử dụng | Validation chính |
|---|---|---|---|---|
| products | productCode, category, attributes, tags | category/attributes embedded, tags array | `/san-pham`, `/api/products` | mã duy nhất, giá/tồn kho không âm |
| promotions | conditions, targets | embedded và array | `/khuyen-mai`, `/api/promotions` | ngày, loại giảm, giá trị, giới hạn |
| customers | customerCode, email | document | `/khach-hang`, `/api/customers` | mã/email duy nhất, level/status |
| reviews | productCode, customer | customer snapshot, productName/productImage snapshot; orderCode khi gửi từ đơn | `/danh-gia`, `/api/reviews`, `/account/orders/<code>/reviews` | rating 1–5, khách đã mua trong đơn confirmed/completed; snapshot do máy chủ gán |
| orders | customerCode, items, appliedPromotion | reference logic + embedded snapshot | `/don-hang`, `/api/orders` | đọc đúng items/promotion hiện hữu |

