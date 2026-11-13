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


## Personal profile extension (optional, backward compatible)

Existing customerCode and all relationships remain unchanged. Additional customers fields:

| Field | Storage / validation |
|---|---|
| fullName | Required string, trimmed, maximum 200 characters. Omitted in PATCH-style update means retain existing. |
| phone | Optional Vietnam mobile/landline, normalized separators, local 0… or international +84… notation. |
| dateOfBirth | Optional ISO date string YYYY-MM-DD; real date, at most today's Vietnam date. |
| gender | Optional male/female/other/undisclosed. |
| address | Optional trimmed string, maximum 500 characters. |
| bio | Optional trimmed string, maximum 300 characters. |
| avatar | Optional object: key (random 64 hex + .webp), mediaType=image/webp, width/height <=512, updatedAt (UTC BSON datetime). No binary. |

An omitted field stays unchanged. An explicitly empty optional field is removed with $unset. fullName cannot be explicitly empty. Updates use $set/$unset rather than document replacement. Avatar metadata is writable only through dedicated avatar service, never the profile API. Login email remains in users and is read-only in the profile UI; customers.email remains the pre-existing business field. role/level/status/passwordHash/authVersion/customerCode are not editable through profile endpoints. Existing admin customer forms keep using $set and retain the new fields.

Files are private in AVATAR_STORAGE_DIR, backed by avatar_data in Docker, excluded from Git/build context. Back up the database and volume together. Deleting a customer document does not authorize deleting arbitrary files. The cleanup-avatar-orphans CLI removes only unreferenced generated files older than 24 hours, under the account lock, with dry-run as default.

## Staff own-account profiles

For non-CUSTOMER roles, users.profile is an optional object containing fullName/phone/dateOfBirth/gender/address/bio and optional avatar metadata with the same validations as the customer profile fields above. No migration or synthetic customer record is required. Existing accounts without profile display the login email prefix until a name is saved. Role and login email remain read-only at the top level of users. All updates use profile.field dot paths and retain passwordHash/authVersion/status and business links. CUSTOMER continues using customers, preserving its shopping relationships. The avatar_data volume is shared storage, but each user's reference and private image endpoint are scoped to the session user. Cleanup must scan both metadata locations.
