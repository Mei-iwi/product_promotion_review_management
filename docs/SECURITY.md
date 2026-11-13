# Authentication, RBAC và vận hành

Ngày triển khai: 11/11/2026. Baseline: `6f88d79bfadcb797df90b4a5d605c862e7287710`.

Tham chiếu API chính thức khi triển khai: [argon2-cffi PasswordHasher](https://argon2-cffi.readthedocs.io/en/stable/api.html),
[MongoDB atomic findOneAndUpdate](https://www.mongodb.com/docs/manual/reference/method/db.collection.findOneAndUpdate/),
[MongoDB partial unique indexes](https://www.mongodb.com/docs/manual/core/index-partial/).

Giữ Flask → Services → Repositories → PyMongo; không Redis/JWT, không thay aggregation.
Không seed/chuyển đổi customers thành users, không xóa hoặc nạp lại dữ liệu hiện hữu.

## Tạo ADMIN đầu tiên

1. Cài dependency: `python -m pip install -r requirements.txt`.
2. Sao chép `.env.example` sang `.env` nếu chưa có `.env`; giữ URI/database hiện có.
3. Tạo SECRET_KEY bằng `python -c "import secrets; print(secrets.token_hex(32))"`,
   lưu riêng trong `.env`/secret store. Không đưa mật khẩu vào command line hoặc Git.
4. Local HTTP dùng `APP_ENV=development`. Production dùng `APP_ENV=production` và HTTPS.
5. Chạy `python -m flask --app app:create_app bootstrap-admin`.
6. Nhập email và mật khẩu hai lần tại prompt ẩn. CLI chỉ tạo ADMIN khi chưa có ADMIN;
   khóa MongoDB đồng bộ cả bootstrap và các thao tác tài khoản khác.
7. Mở `/login`; ADMIN tạo tài khoản trong `/admin/users/create`. Không có đăng ký công khai.

Không có tài khoản hoặc mật khẩu demo mặc định. Mật khẩu 8–128 ký tự, hỗ trợ cụm từ,
chặn mật khẩu phổ biến, ít ký tự khác nhau hoặc chứa phần định danh email.
Argon2id: memory=19456 KiB, time=2, parallelism=1; hash tự rehash nếu đổi cấu hình.
Benchmark máy kiểm thử: 10 hash, median 22.11 ms, max 23.04 ms.
Đây là cấu hình tối thiểu để giới hạn bộ nhớ khi nhiều worker/thread xác minh đồng thời;
benchmark lại hạ tầng production trước khi tăng memory/time (8 luồng đồng thời ~152 MiB bộ nhớ Argon2).

## Demo các vai trò

Đã bổ sung **ACCOUNT_MANAGER — Quản trị viên tài khoản**, quản lý tại `/admin/users`,
chỉ quản lý tài khoản CUSTOMER. ADMIN quản lý mọi tài khoản và cấp/thu hồi ACCOUNT_MANAGER.
Xem [hướng dẫn quản lý tài khoản](ACCOUNT_MANAGEMENT.md) cho phạm vi, bộ lọc, phân trang,
xác thực lại, xác nhận trên giao diện và hợp đồng API giữ nguyên data là mảng.

ADMIN tạo từng tài khoản với mật khẩu riêng; CUSTOMER cần một customerCode tồn tại và active.
Một customerCode chỉ được gắn với một CUSTOMER. Nhân viên không có customerCode.
Đăng xuất rồi đăng nhập tài khoản tương ứng; mọi vai trò vào `/catalog`, bỏ qua `next`.

| Role | Trang sau đăng nhập | Thao tác demo |
|---|---|---|
| ADMIN | `/catalog` | Quản lý user, gán role, tất cả báo cáo, duyệt review; không tạo review thay khách |
| ACCOUNT_MANAGER | `/catalog` | Chỉ xem/tạo/vô hiệu hóa/kích hoạt/mở khóa/reset mật khẩu CUSTOMER |
| PRODUCT_STAFF | `/catalog` | CRUD sản phẩm; chỉ xóa sản phẩm createdByApp |
| MARKETING_STAFF | `/catalog` | CRU khuyến mãi; đọc sản phẩm |
| SUPPORT_STAFF | `/catalog` | CRU hồ sơ, xem đơn; không thay quyền đăng nhập |
| REVIEW_MODERATOR | `/catalog` | Duyệt/từ chối; không duyệt review có cùng createdByUserId |
| ANALYST | `/catalog` | Tổng hợp NC01/02/03/05/06/07/08/09; không NC04/10 hoặc báo cáo chi tiết |
| CUSTOMER | `/catalog` | Hồ sơ, đơn/review của mình, gửi review pending với xác minh mua hàng |

Guest vào `/catalog`, `/catalog/<code>` hoặc API `/api/public/...`; chỉ active products và
approved reviews, projection bỏ stock/attributes/định danh khách hàng.
`/health` là ngoại lệ readiness công khai, không trả dữ liệu nghiệp vụ.

Ma trận chi tiết: [RBAC_MATRIX.md](RBAC_MATRIX.md). Toàn bộ route/method:
[SECURITY_ROUTES.md](SECURITY_ROUTES.md). Kiểm kê ban đầu: [SECURITY_AUDIT.md](SECURITY_AUDIT.md).
Mọi endpoint chưa khai báo đều deny; HEAD theo GET, OPTIONS theo policy method đã khai báo.
API lỗi dùng `{success,message,data}`, guest 401, thiếu quyền 403. Web guest redirect `/login`.
Đơn riêng không thuộc sở hữu trả 404; mọi truy vấn riêng dùng customerCode từ principal.

## Schema và indexes bổ sung

| Collection | Schema | Index |
|---|---|---|
| users | ObjectId, email/emailNormalized, passwordHash, role, status, customerCode (CUSTOMER), authVersion, failedLoginCount, lockedUntil, passwordChangedAt, createdAt/updatedAt/lastLoginAt | unique emailNormalized; unique partial customerCode khi role=CUSTOMER và customerCode kiểu string |
| sessions | sessionIdHash, userId (null cho phiên trước login), csrfToken, createdAt/lastSeenAt, idleExpiresAt/absoluteExpiresAt, revokedAt, authVersionAtIssue | unique sessionIdHash; userId; TTL absoluteExpiresAt=0 |
| audit_logs | actorUserId, action, resourceType/resourceId, timestamp, result, requestId, ipAddress, metadata | timestamp descending; actorUserId+timestamp |
| security_limits | _id (IP/email hash theo mục đích), count, expiresAt | _id unique mặc định; TTL expiresAt=0 |
| security_locks | _id=`user-mutations`, owner ngẫu nhiên, createdAt | _id unique mặc định; không TTL/lease |

Indexes được tạo bổ sung và kiểm tra định nghĩa, không drop/rebuild collection cũ.
Tên và cấu hình chính xác: [SECURITY_INDEXES.md](SECURITY_INDEXES.md).
Quy tắc schema/role/foreign key được validate trong service; database credential chỉ dùng cho ứng dụng.
Session token ngẫu nhiên 256 bit nằm trong cookie; chỉ SHA-256 token được lưu trong MongoDB.
CSRF là synchronizer token độc lập lưu phía server (giá trị plaintext được phép, không log).
Phiên trước login cũng nằm trong MongoDB, rotate và revoke khi login thành công.
Không lưu role, userId hoặc session token trong localStorage/sessionStorage.

Kiểm tra revoked, idle 30 phút, absolute 8 giờ và authVersion trực tiếp mỗi request,
không phụ thuộc TTL cleanup. Đổi password/role/status thu hồi các phiên ngay.
Customer inactive tăng authVersion và revoke, nên kích hoạt lại hồ sơ không phục hồi cookie cũ.
Khóa do sai password 5 lần trong cửa sổ 15 phút tự hết hạn sau tối đa 15 phút.
Mỗi IP tối đa 20 lần thử trong cửa sổ 15 phút; mọi reservation dùng cập nhật MongoDB atomic.
Không tin X-Forwarded-For; remote_addr là nguồn IP.

Audit ghi login/logout, lock, password, user/role, access denied, sửa promotion và moderation.
Metadata được tạo từ allowlist tại call site; không đưa request body, password, hash hoặc token vào audit.
MongoDB là nguồn quyền hiện hành; không cấp permission trực tiếp cho từng user.

## Bảo vệ ADMIN và phục hồi khóa

Tất cả mutation user được tuần tự hóa bằng insert document khóa có _id duy nhất trong MongoDB.
Việc đếm ADMIN active và cập nhật nằm trong cùng critical section; request cạnh tranh nhận 409,
không dùng Python lock hoặc count-then-update không đồng bộ. ADMIN cuối không được demote/disable/lock.
Cấp ADMIN, sửa ADMIN và reset password nhân viên yêu cầu actorPassword hiện tại.
Không có API xóa user. Các thay đổi role/status/reset làm tăng authVersion.

Khóa không có lease: nếu worker chết giữa critical section, thao tác quản trị bị chặn.
Đây là đánh đổi availability để tránh hai owner cùng ghi sau khi lease hết hạn.
Khi xác nhận khóa mồ côi: dừng **tất cả** app worker/container và CLI writer; backup và kiểm tra
users/audit/security_locks; chỉ operator mới được xóa đúng document `_id: user-mutations`, rồi khởi động lại.
Không xóa khóa khi còn writer chạy. Chưa có quy trình phục hồi tự động hoặc lease-based takeover.
Quản trị trực tiếp DB nằm ngoài bảo vệ RBAC; không chia sẻ credential ứng dụng cho nhân viên.

## CSRF và hardening

Mọi POST/PUT/PATCH/DELETE (kể cả login/logout) cần token server session; form có csrf_token,
AJAX cùng origin dùng X-CSRF-Token. Không miễn CSRF cho test hoặc API.
Whitelist/type validation chặn mass assignment, Mongo operator/dot path, NaN/Infinity;
tìm kiếm regex escape input. Jinja autoescape; dashboard dùng escapeHtml/textContent.
CSP cho self và jsDelivr Bootstrap; script không cho unsafe-inline, style cho inline phục vụ Bootstrap/SVG.
Nosniff, frame deny, same-origin referrer, no-store và giới hạn body 1 MiB.
HSTS chỉ trả trên HTTPS. Production fail fast nếu SECRET_KEY thiếu/ngắn/ít đa dạng ký tự.
Cookie `__Host-auth`: Secure, HttpOnly, SameSite=Lax, Path=/, không Domain; dev dùng dev-auth.
Flask cookie riêng chỉ phục vụ flash message, không xác thực hay lưu permission.

## Docker và MongoDB

Local demo HTTP: `APP_ENV=development`. Production: `APP_ENV=production`, HTTPS thật tới Gunicorn
hoặc TLS termination qua proxy có IP tin cậy cố định; không mở backend cho nguồn tùy ý.
Gunicorn mặc định chỉ tin secure-scheme headers từ loopback; khi reverse proxy khác máy,
cấu hình `GUNICORN_CMD_ARGS=--forwarded-allow-ips=<exact-proxy-IP>` và giới hạn network tương ứng.
Không dùng `*`. Ứng dụng không tin X-Forwarded-For; sau proxy rate limit dùng IP proxy nên bảo thủ hơn.
Healthcheck nội bộ `/health` qua loopback được phép HTTP, các route khác vẫn bắt buộc HTTPS.

Compose yêu cầu SECRET_KEY, MONGO_ROOT_USERNAME/PASSWORD và MONGO_APP_USERNAME/PASSWORD.
`FLASK_PORT=5002` điều khiển cổng web của stack duy nhất; không chạy thêm Flask local.
MongoDB replica set rs0 xuất tại `MONGO_DOCKER_PORT=27018`, chung database cho mọi tính năng.
Dùng username URI-safe và password hex ngẫu nhiên; không commit `.env`.
MongoDB bật --auth; script docker-init-user.js chỉ chạy trên data directory **trống**,
tạo user readWrite đúng một database, không seed dữ liệu nghiệp vụ.

**Volume MongoDB đã tồn tại:** trước khi bật --auth, operator phải cấu hình root và application user
trên server hiện tại bằng công cụ quản trị an toàn. Init script không chạy lại trên volume có dữ liệu.
Không down -v, không chạy lại DB.js và không drop dữ liệu để giải quyết lỗi credential.
Compose cấp URI có credential readWrite đúng database, authSource, replicaSet=rs0 và directConnection=true;
credential ứng dụng không dùng root. Chạy migrate/backup bằng credential operator riêng.

Tạo ADMIN trong container bằng `docker compose exec app python -m flask --app app:create_app bootstrap-admin`.
Build dùng user không đặc quyền, Gunicorn 2 workers × 4 threads; healthcheck ping MongoDB.

## Kiểm thử có thể chạy lại

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
docker build -t promotion-rbac:verify .
python scripts/verify_security_runtime.py
python scripts/export_security_policy.py
```

Kiểm thử giao diện tùy chọn trên Windows có Microsoft Edge:
`python -m pip install playwright==1.65.0`, rồi `python scripts/verify_security_browser.py`.
Đã kiểm tra trình duyệt Edge headless ở 1440×1000 và 390×844: login, admin, customer,
form, menu và logout; không tràn ngang. Ảnh bằng chứng nằm trong `docs/security-ui/`.

Lệnh pytest độc lập bỏ qua 3 integration test nếu không có SECURITY_TEST_MONGO_URI.
Verifier tạo MongoDB xác thực riêng, random database/container/network, chạy **toàn bộ suite**
kèm integration, rồi kiểm tra hai ứng dụng độc lập và replay cookie qua HTTP. Không dùng MongoDB hiện có.
Cleanup chỉ xóa container/anonymous volume mang tên ngẫu nhiên do chính lần chạy tạo.
JUnit và bảng tên test nằm ở [security-test-results.xml](security-test-results.xml),
[SECURITY_TESTS.md](SECURITY_TESTS.md). Không có cơ chế tắt authentication/authorization/CSRF trong test.

## Giới hạn còn lại

- Không có MFA, email recovery, public registration hoặc dịch vụ gửi password; ngoài phạm vi yêu cầu.
- Khóa user mutation có thể cần operator phục hồi sau crash; cần giám sát audit/lock và backup MongoDB.
- Rate limit cửa sổ 15 phút bắt đầu ở request đầu tiên, dùng atomic reservation; không phải sliding log.
- Phụ thuộc CDN Bootstrap cho giao diện; CSP cho phép đúng origin CDN. Chưa kiểm thử TLS certificate/proxy
  trên hạ tầng production của người dùng; Docker runtime kiểm thử ở development HTTP, production flag/cookie/HTTPS được test riêng.
- Kiểm thử trình duyệt dùng Edge ở hai kích thước viewport; chưa kiểm chứng mọi trình duyệt/thiết bị.
- Audit và mutation không nằm trong multi-document transaction trên standalone MongoDB; lỗi DB/crash giữa
  mutation và audit có thể cần đối soát. Không khẳng định khả năng chống mọi cuộc tấn công từ các test hiện có.
- Test Mongomock trên Python 3.13 phát cảnh báo datetime.utcnow từ dependency, không phải lỗi kiểm thử.
