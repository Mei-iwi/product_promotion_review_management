# Khu mua sắm khách hàng

Giữ Flask → route → service → repository → PyMongo; dùng lại Bootstrap/Jinja và RBAC/CSRF hiện có.
Danh mục/chi tiết công khai vẫn ở `/catalog` và `/catalog/<code>`. Khách hàng dùng
`/cart`, `/account`, `/account/orders`, `/account/reviews`. Không có đăng ký công khai hoặc thanh toán online.

Chỉ được gửi đánh giá khi chính khách hàng đã mua sản phẩm trong đơn `confirmed` hoặc `completed`.
Máy chủ chặn cả Web và API đối với sản phẩm chưa mua, đơn pending/cancelled hoặc đơn của người khác.
**Đơn hàng của tôi** nằm trực tiếp trên thanh điều hướng. Trong chi tiết đơn confirmed/completed,
mỗi sản phẩm có biểu mẫu đánh giá ngay trên trang, kể cả sản phẩm đã ngừng bán.
POST `/account/orders/<code>/reviews` kiểm tra chủ đơn, trạng thái và sản phẩm thuộc đúng đơn;
CSRF bắt buộc, lỗi giữ các giá trị đã nhập. Gửi thành công quay lại chi tiết đơn, đánh giá luôn pending.
Trang sản phẩm dẫn khách đủ điều kiện về đơn hàng để đánh giá.

**Đánh giá của tôi** ở menu **Tài khoản** là trang chỉ xem, không có form gửi đánh giá.
Chỉ liệt kê đánh giá của khách đang đăng nhập, kèm tên/ảnh sản phẩm, điểm, nội dung, thời gian và trạng thái.
Review mới lưu snapshot tên/ảnh sản phẩm và mã đơn (khi gửi từ đơn) để giữ lịch sử khi sản phẩm bị xóa.
API tạo đánh giá cũ vẫn kiểm tra đã mua và không nhận trường snapshot/mã đơn do client gửi.
Hồ sơ và Đổi mật khẩu vẫn ở menu **Tài khoản**, không có dãy nút lặp lại trên trang cá nhân.

Kiểm tra cập nhật luồng đánh giá: **224 passed, 15 skipped**; 15 kiểm thử replica chạy riêng đạt.

## Xem và chọn mã giảm giá

Mục **Mã giảm giá** trên thanh điều hướng mở `/vouchers`, chỉ xem được sau khi đăng nhập.
Khách chưa đăng nhập không thấy tab này; truy cập URL trực tiếp được chuyển về `/login`.
Trang phân trang 12 mã, hiển thị ưu đãi, đơn tối thiểu, mức giảm tối đa, sản phẩm/nhóm hàng,
thời hạn và trạng thái. Chỉ công khai mã active còn hạn; mã sắp bắt đầu hoặc hết lượt được ghi rõ.
Không công khai audit hoặc số lượt đã dùng. CUSTOMER có giỏ phù hợp có thể bấm **Dùng mã này**.

Giỏ hàng và trang xác nhận COD có danh sách mã phù hợp, xếp số tiền giảm từ cao xuống thấp.
Danh sách dùng cùng phép tính với checkout, kiểm tra giá trị đơn, phạm vi sản phẩm/nhóm,
thời gian và lượt còn lại. Chỉ gợi ý mã giảm được số tiền lớn hơn 0; mỗi đơn dùng một mã.
Khách vẫn có thể nhập mã trực tiếp trong giỏ hoặc chọn **Không dùng mã giảm giá**.

Ở checkout, chọn mã rồi bấm **Áp dụng mã**. Máy chủ tạo xác nhận mới với tổng tiền mới,
giữ các ô thông tin nhận hàng, không trừ tồn/lượt mã hoặc tạo đơn. Form đặt hàng gửi về
đúng xác nhận mới. Nếu chọn mã khác mà chưa áp dụng, máy chủ yêu cầu áp dụng lại trước khi đặt.
Xác nhận cũ/hết hạn hoặc thuộc người khác bị từ chối. Lượt mã vẫn được kiểm tra và giữ
trong transaction khi đặt thành công, không giữ lượt lúc xem hay chọn mã.

Kiểm tra cập nhật: `python -m pytest -q` → **222 passed, 15 skipped**.
15 kiểm thử MongoDB replica chạy riêng thành công; trình duyệt kiểm tra chọn mã trong giỏ,
bỏ/chọn lại mã ở checkout, giữ số điện thoại, đặt COD và các bước quản lý đơn tiếp theo.

## Hình sản phẩm và trang sau đăng nhập

50 sản phẩm demo dùng ảnh WebP tại `static/img/products/`, đã gắn trường `image` vào
database dùng chung. Nguồn tải và checksum nằm trong `data/demo/product-images.json`.
Danh mục, chi tiết công khai và trang quản lý đều hiển thị ảnh. Không cần kết nối
đến website nguồn khi xem sản phẩm. Tạo lại JSON demo vẫn giữ đường dẫn ảnh.

Mọi vai trò đăng nhập thành công đều vào `/catalog`; bỏ qua tham số `next` từ client.
Các tab quản lý và quyền API vẫn giữ phạm vi hiện có.

Kiểm tra cập nhật: **213 passed, 15 skipped** trong bộ pytest; kiểm tra đăng nhập 8 vai trò,
50 URL ảnh trả HTTP 200/image-webp và hiển thị desktop/mobile không tràn ngang.
Edge kiểm tra luồng đăng nhập ADMIN/ACCOUNT_MANAGER/CUSTOMER trên fixture cô lập thành công.

## Chạy demo với replica set có xác thực

### Hợp nhất môi trường ngày 11/11/2026

Web quản lý và mua sắm hiện dùng chung cổng **5002**, MongoDB Docker cổng **27018**.
Các bản web cũ ở 5001/5003 đã dừng. Đã sao lưu ba database ứng dụng vào
`backup/unified-20261111T163404Z/`, rồi chuyển từ MongoDB local sang volume Docker hiện có:
50 sản phẩm, 20 khuyến mãi, 2 tài khoản, 1 hồ sơ khách hàng và 33 bản ghi audit.
Đã đối chiếu document sau khi chuyển; giữ nguyên ID và hash mật khẩu, không chuyển phiên đăng nhập.
Database local và volume của stack mua sắm cũ vẫn được giữ làm nguồn đối chiếu.
Sau chuyển đã bật rs0 và đối soát 20 mã thành công; không thay đổi tồn kho đơn cũ.

Kiểm tra sau hợp nhất: `python -m pytest -q` → **205 passed, 15 skipped**;
script `verify_shopping_compose.py` kiểm tra stack mới từ volume trống thành công.
Web `/health`, `/login`, `/catalog` trả 200. Chưa thực hiện đặt đơn thật trên dữ liệu người dùng.

Dùng một `docker-compose.yml` cho quản lý và mua sắm, chung database.
Giữ volume `mongodb_data` hiện có khi bật replica set; không chạy hai stack song song:

```bash
docker compose up --build -d
docker compose ps
```

Yêu cầu `.env` có SECRET_KEY ngẫu nhiên và MONGO_ROOT_USERNAME/PASSWORD,
MONGO_APP_USERNAME/PASSWORD (password hex/username URI-safe như cấu hình Docker hiện tại).
Keyfile replica set được tạo trong volume riêng, quyền 400; app chỉ nhận credential readWrite của database.
Script init chỉ khởi tạo rs0 khi chưa có cấu hình, không drop/seed dữ liệu.

| Thành phần | Địa chỉ mặc định |
|---|---|
| Web mua sắm replica set | http://127.0.0.1:5002 |
| MongoDB replica set, nhìn từ host/Compass | localhost:27018 |
| Replica set | rs0, một node cho phát triển |
| Database | QL_KHUYENMAI_DANHGIA hoặc MONGO_DB trong .env |

`FLASK_PORT`, `MONGO_DOCKER_PORT` đổi hai cổng trên. Nội bộ app kết nối service mongodb:27017,
`replicaSet=rs0&directConnection=true`; không dùng localhost bên trong app container.
Kết nối Compass từ host có authSource là database ứng dụng, replicaSet=rs0 và directConnection=true
(hostname quảng bá trong Docker là mongodb nên cần directConnection khi nối cổng host).

### Nếu tạo database demo mới

1. Import `data/demo/products.json` vào products và `promotions.json` vào promotions, đúng MongoDB cổng 27018.
   Giữ định dạng Extended JSON `$date` để ngày là BSON Date.
2. Đối soát trước khi checkout:

```bash
docker compose exec app python -m flask --app app:create_app reconcile-promotion-usage
```

3. Tạo ADMIN một lần nếu database mới chưa có:

```bash
docker compose exec app python -m flask --app app:create_app bootstrap-admin
```

4. ADMIN tạo hồ sơ khách hàng active rồi tạo tài khoản CUSTOMER liên kết hồ sơ đó.
   Không có password/user cố định được seed. ACCOUNT_MANAGER chỉ tạo tài khoản CUSTOMER,
   không tự tạo hồ sơ nghiệp vụ hoặc tự cấp quyền.
5. CUSTOMER đăng nhập cổng 5002 → Danh mục → tìm/lọc → chi tiết → thêm giỏ → áp mã →
   xem lại/thanh toán → nhập số điện thoại → đặt COD → xem chi tiết đơn.
6. Dùng ADMIN mở đơn trong `/don-hang` để xác nhận rồi hoàn tất.
   CUSTOMER có thể đánh giá từ dòng hàng sau khi confirmed/completed; đánh giá mới pending.
7. Dùng một đơn pending khác để thử khách hủy: tồn kho và lượt mã được trả đúng một lần.

Giá, tồn, tên và mức giảm của đơn được chụp tại lúc đặt. Giao hàng 0 ₫; tổng tiền phải trả
hiện rõ trên trang xem lại và nút Đặt hàng. COD không gọi cổng thanh toán.

### Giữ dữ liệu local/standalone hiện có khi chuyển sang replica set

Không xóa volume, không down -v stack hiện tại, không chạy lại DB.js có lệnh xóa.
Giữ hệ thống cũ làm nguồn/rollback; dừng các writer trong thời gian backup/import/đối soát lần đầu.

1. Backup database nguồn bằng mongodump (MongoDB Database Tools), ví dụ nguồn local:

```bash
mongodump --uri="mongodb://127.0.0.1:27017" --db=QL_KHUYENMAI_DANHGIA --out=backup/before-shopping
```

2. Khởi động stack chính và kiểm tra database đích chưa có dữ liệu nghiệp vụ cần giữ.
   Restore backup vào **đúng đích 27018**, giữ nguyên collection users để giữ tài khoản/hash hiện có.
   Dùng thông tin xác thực đích do bạn quản lý; không ghi password vào Git hoặc command history.
   Ví dụ mongorestore hỏi password tương tác (thay USER_NAME bằng MONGO_APP_USERNAME):

```bash
mongorestore --host=127.0.0.1 --port=27018 --username=USER_NAME --authenticationDatabase=QL_KHUYENMAI_DANHGIA --nsInclude="QL_KHUYENMAI_DANHGIA.*" backup/before-shopping
```

3. Không dùng `--drop`. Nếu đích đã có tài khoản/business records thì dừng và đối chiếu mã/index
   trước khi merge; không restore đè hoặc xóa tự động. Kiểm tra số lượng document nguồn/đích.
4. Chạy reconcile-promotion-usage trên đích trước khi cho khách đặt. Chuyển truy cập sang web 5002.
   Cookie cũ không cần copy, khách đăng nhập lại. Giữ bản backup và nguồn cũ để quay lại nếu cần.

Giữ nguồn và backup để đối chiếu. Các script verification chỉ dùng project ngẫu nhiên,
không thao tác trên dữ liệu thật.

### Chạy app local với một replica set đã cấu hình

Đặt MONGO_URI có replicaSet/directConnection/authSource đúng server và `CHECKOUT_ENABLED=true`,
khởi động lại app sau khi đối soát. URI/password thực nằm trong `.env` hoặc secret store.
`CHECKOUT_ENABLED=false` là mặc định khi chạy app ngoài Compose. Compose chính đặt true,
nhưng vẫn chặn checkout cho tới khi có marker đối soát thành công trong shopping_state.

Trên standalone: danh mục, giỏ và tra cứu vẫn hoạt động; checkout trả 503 trước khi trừ tồn,
giữ lượt hay ghi đơn. Không dùng transaction giả hoặc fallback ghi từng collection.
Một node rs0 chỉ phù hợp demo/phát triển, chưa phải cấu hình HA production.

## Dữ liệu và nhất quán

| Collection / trường | Ý nghĩa |
|---|---|
| carts | `_id=userId`, userId, customerCode, items[{productCode,quantity}], promoCode, version, updatedAt. Mỗi dòng 1–99, tối đa 50 mã khác nhau. |
| checkout_quotes | Khóa ngẫu nhiên theo user/customer, lines/totals, fingerprint server-side, cartVersion, createdAt/expiresAt. TTL expiresAt, hiệu lực 15 phút kiểm tra trực tiếp. |
| orders | Giữ orderCode/customerCode/orderDate/items/productName/quantity/unitPrice/appliedPromotion/totalAmount/status cũ; thêm subtotal, shippingFee=0, paymentMethod=COD, recipient và statusHistory. |
| orders.checkoutKey + customerCode | Unique partial index khi checkoutKey là string. requestHash gắn cùng khóa với cùng recipient/quote; gửi lại khác nội dung trả 409. |
| orders.commerceVersion, inventoryReserved | Đánh dấu đơn luồng mới đã trừ tồn. Đơn cũ thiếu marker không được hoàn tồn. |
| orders.promotionUsageAccounted | Lượt mã đã được ghi vào bộ đếm; reconciliation gắn marker này cho đơn cũ còn hiệu lực. Chỉ trả lượt khi có marker rõ ràng, xóa marker trong transaction hủy. |
| promotions.commerceUsed | Số đơn pending/confirmed/completed đang dùng mã sau đối soát, gồm cả đơn cũ; không tăng khi áp thử mã. usageLimit=0 không giới hạn nhưng vẫn đếm. |
| shopping_state | `_id=promotion-usage-v1`, ready, schemaVersion=1, epoch, reconciledAt. Là hàng rào ghi chung giữa checkout, đổi trạng thái và đối soát. |

Carts dùng compare-and-swap version để tránh mất cập nhật giữa cửa sổ/worker. Giá không lưu làm nguồn
tin cậy trong giỏ; mỗi lần xem/tính lại đều đọc sản phẩm và chương trình từ server.
Quote fingerprint chứa snapshot server-side (không trả số tồn chính xác). Khi giá/tồn/ưu đãi hoặc
version giỏ thay đổi, không chấp nhận tổng tiền mới âm thầm: khách phải xem lại giỏ và tạo quote mới.
Recipient lỗi được giữ trên form, có lỗi cạnh trường tương ứng; không cập nhật hồ sơ người mua.

Checkout transaction snapshot/majority: đọc lại principal và dữ liệu → trừ tồn có điều kiện →
tăng commerceUsed có giới hạn → ghi order/snapshot/audit → xóa giỏ có điều kiện version.
Callback không có side effect ngoài MongoDB, dùng `with_transaction` để retry conflict/commit theo driver.
Ngay khi thấy order đã có cùng customerCode+checkoutKey, trả lại order cũ nếu requestHash trùng,
kể cả giỏ đã được sửa sau đó hoặc quote đã hết hạn. Không trừ tồn/giữ mã/xóa giỏ lần hai.

Trạng thái: pending → confirmed → completed; chỉ pending → cancelled. CUSTOMER chỉ hủy của mình;
ADMIN có permission ghi riêng orders.manage_status. SUPPORT_STAFF vẫn chỉ đọc.
completed/cancelled là trạng thái cuối. Hủy và xác nhận cạnh tranh chỉ một nhánh commit.
Hủy repeat trả lại cancelled hiện có, không lặp event/refund. Hủy đơn mới pending hoàn tồn và lượt
trong cùng transaction. Hủy đơn cũ không hoàn tồn; chỉ trả lượt nếu đã được đối soát/đánh dấu.

Reconcile chạy một transaction: lấy số đơn cũ/mới pending/confirmed/completed theo promoCode,
ghi lại commerceUsed (không cộng dồn), đánh dấu contribution của các order đó và ready.
Gửi lại lệnh không làm tăng lượt. Không sửa giá, số tiền hoặc tồn kho của đơn cũ.
Các writer mới đều ghi epoch nên đối soát và checkout/status bị serialize bằng write conflict/retry.
Đánh đổi: đây là điểm ghi chung, phù hợp quy mô demo, cần phân tích lại throughput cho production lớn.
Không import/chỉnh trực tiếp đơn hàng song song bên ngoài các service; dừng writer ngoài ứng dụng khi đối soát.

## Mã giảm giá và thời gian

- Active, UTC startDate ≤ now ≤ endDate, đủ lượt, subtotal toàn giỏ ≥ minOrderValue.
- Hai targets rỗng: áp cho tất cả dòng. Có targets: productCode HOẶC categoryCode, khớp cả hai chỉ tính một lần.
- Percentage tính trên tổng dòng đủ điều kiện, Decimal và ROUND_HALF_UP đến đồng.
- Fixed trừ một lần/đơn. Giảm không vượt tiền đủ điều kiện; maxDiscount>0 tạo trần, 0 là không trần riêng.
- Mã lỗi phân biệt: không tồn tại, inactive, chưa đến ngày, hết hạn, hết lượt, thiếu tiền tối thiểu, thiếu sản phẩm phù hợp.
- Ví dụ 800.000đ, eligible 500.000đ, 10%, trần 40.000đ, min 700.000đ → giảm 40.000đ, trả 760.000đ.

Đã kiểm tra form quản trị cũ dùng datetime-local và parse_date lưu datetime không timezone;
PyMongo coi giá trị đó là UTC. Không tự dịch lại BSON Date hiện có vì không suy ra ý định múi giờ cũ.
Từ thay đổi này, **input mới không có timezone được hiểu là giờ Việt Nam**, chuyển sang UTC trước lưu;
input có offset/Z tôn trọng offset. Form edit hiển thị UTC→Việt Nam, save lại giữ nguyên instant.
Extended JSON `$date` đã import vẫn là UTC. Bộ lọc promotion, checkout và hiển thị thời gian không dùng
timezone của execution host. Các timestamp mới của order/audit/quote lưu UTC, hiển thị UTC+7.

## Bảo vệ dữ liệu và route

Projection danh mục chỉ gồm tên/brand/giá/category, inStock boolean, ảnh và thống kê approved.
Chi tiết chỉ thêm allowlist thuộc tính công khai; không trả stock chính xác/internalCost/supplier data.
Reviews công khai chỉ approved, không trả customer snapshot/customerCode/userId.
Cart/quote/order riêng luôn ràng buộc userId/customerCode từ session, không nhận owner/giá/tổng/verifiedPurchase/status từ client.
Mọi mutation Web/API dùng CSRF hiện có. Unknown endpoints tiếp tục deny-by-default.

| Nhóm route mới | Permission |
|---|---|
| GET /cart, GET /api/account/cart | cart.read_own |
| POST /cart/items, POST sửa/xóa dòng, POST áp/bỏ mã; API POST/PUT/DELETE tương ứng | cart.manage_own |
| POST /checkout/quote, GET/POST /checkout/&lt;key&gt;, POST /api/account/checkout/quotes, POST /api/account/checkout | orders.create_own |
| GET /account/orders/&lt;code&gt;/confirmation | orders.read_own |
| POST /account/orders/&lt;code&gt;/cancel, POST /api/account/orders/&lt;code&gt;/cancel | orders.cancel_own |
| POST /don-hang/&lt;code&gt;/trang-thai, PATCH /api/orders/&lt;code&gt;/status | orders.manage_status |

Chi tiết từng endpoint/method: [SECURITY_ROUTES.md](SECURITY_ROUTES.md);
ma trận: [RBAC_MATRIX.md](RBAC_MATRIX.md); schema: [SCHEMA.md](SCHEMA.md).
API checkout quote trả checkoutKey và các khoản tiền. API checkout nhận đúng checkoutKey/fullName/address/phone,
phản hồi envelope hiện có. Cùng key replay vẫn trả orderCode cũ, không tạo checkout attempt mới.

## Kiểm thử và phần chưa xác minh

```bash
source .venv/Scripts/activate
python -m pytest -q
python scripts/verify_shopping_replica.py
python scripts/verify_shopping_compose.py
```

- Suite thông thường: **205 PASS, 15 SKIP**, không FAIL. Các SKIP cần MongoDB thật, không bỏ auth/CSRF.
- Replica suite riêng: **15 PASS**, gồm 12 shopping cases và 3 MongoDB security cases hiện hữu.
  Kiểm tra sản phẩm/lượt mã cuối giữa hai khách, double checkout, replay request khác, hủy-vs-xác nhận,
  trạng thái cuối, rollback khi lỗi trước ghi đơn/sau ghi đơn, quote thay đổi/hết hạn/sai chủ,
  đối soát lặp và legacy không hoàn tồn, snapshot tiền và xác minh review.
- Browser thực trên replica set: desktop 1440×1000, mobile 390×844; toàn bộ luồng mua hàng/áp mã/COD,
  Admin xác nhận/hoàn tất, review pending và khách hủy đơn khác, không tràn ngang.
- Compose replica có keyfile/auth: build, rs-init, app health/catalog/login, CLI đối soát PASS trên project thử nghiệm riêng.
- Python compileall, node --check và git diff --check PASS.
- [shopping-unit-results.xml](shopping-unit-results.xml), [shopping-replica-results.xml](shopping-replica-results.xml),
  [từng test và kết quả](SHOPPING_TESTS.md),
  [ảnh desktop](shopping-ui/desktop-catalog.png), [ảnh mobile checkout](shopping-ui/mobile-checkout.png).

Chưa triển khai/chuyển dữ liệu thật sang replica set, chưa kiểm thử production HA/failover nhiều node,
TLS/proxy production, tải lớn hoặc thiết bị ngoài Edge/hai viewport. Cảnh báo Mongomock datetime và
quyền ghi cache Pytest không làm test fail. Chưa cung cấp dịch vụ vận chuyển, thanh toán online hoặc hoàn tiền.
Không tự import/reset dữ liệu, tạo tài khoản thật, commit/push hay thay stack hiện hữu trong quá trình kiểm thử.

Tham chiếu: [PyMongo transactions/callback retries](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/),
[MongoDB transaction snapshot/majority](https://www.mongodb.com/docs/manual/core/transactions/).

## Tệp chính

- `services/catalog_service.py`, `repositories/public_repository.py`: danh mục phân trang/projection/ratings/ảnh.
- `services/cart_service.py`, `services/promotion_pricing.py`, `services/shopping_common.py`: giỏ, validation, tiền và UTC.
- `services/checkout_service.py`, `repositories/shopping_repository.py`: quotes, idempotency, transaction, indexes, reconciliation.
- `services/order_service.py`, `services/shopping_cli.py`: vòng đời đơn/hoàn tồn/lượt và CLI đối soát.
- `routes/shopping_routes.py`, `routes/auth_routes.py`: Web/API và các trang tái sử dụng.
- `services/access_policy.py`, `services/security.py`, `app.py`, `config.py`: quyền, method, initialization, cấu hình/time filters.
- `services/promotion_service.py`, `repositories/promotion_repository.py`: thời gian khuyến mãi UTC/VN.
- `services/customer_account_service.py`, `services/review_service.py`: lọc đơn cá nhân và giới hạn/luồng review.
- `templates/auth/*`, `templates/orders/detail.html`, `templates/promotions/form.html`, `templates/base.html`: UI mua sắm và trạng thái nội bộ.
- `static/css/app.css`, `static/js/app.js`, `static/img/product-placeholder.svg`: responsive, confirmation/processing, fallback ảnh.
- `docker-compose.yml`, `db/init-replica.js`, `.env.example`: dev replica/config flags.
- `tests/test_shopping.py`, `tests/test_shopping_replica.py`, `tests/shopping_support.py`: unit/HTTP/concurrency fixtures.
- `scripts/verify_shopping_replica.py`, `scripts/verify_shopping_browser.py`, `scripts/verify_shopping_compose.py`: môi trường kiểm thử thật riêng.
- `scripts/export_security_policy.py`, README và các tài liệu schema/policy: hướng dẫn, ma trận, route và bằng chứng.
