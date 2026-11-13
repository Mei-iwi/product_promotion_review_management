# Báo cáo bàn giao RBAC, authentication và account security

Ngày 11/11/2026 (Asia/Saigon). Commit gốc: `6f88d79bfadcb797df90b4a5d605c862e7287710`.
Không commit/push/merge/reset. Dữ liệu MongoDB hiện có không bị đọc/sửa/xóa bởi kiểm thử;
các integration test chạy trong container/database riêng được tạo và dọn theo từng lần chạy.

## Trạng thái nghiệm thu

**ACCEPT trong phạm vi source code và các môi trường kiểm thử đã ghi nhận.**
Không đồng nghĩa với chứng nhận an toàn tuyệt đối hoặc đã triển khai production.

Đã triển khai login/logout, Argon2id, session MongoDB, CSRF toàn bộ mutation, RBAC bảy role,
deny-by-default endpoint/method, object-level ownership, quản trị tài khoản, thu hồi session,
chống brute force dùng chung worker, audit, bảo vệ ADMIN cuối và cấu hình production.
CRUD, dashboard và aggregation hiện hữu được giữ; không thêm đặt hàng/thanh toán/xóa nghiệp vụ ngoài phạm vi.

## Bằng chứng kiểm thử

| Nhóm | Kết quả | Phạm vi |
|---|---|---|
| Baseline | 25 PASS | Source trước thay đổi |
| Regression hiện hữu | 25 PASS | Mongo connection mock, CRUD/validation, review verified purchase/moderation, dashboard và UI cũ; HTTP fixture login thật |
| Authentication service | 5 PASS | Argon2id, bootstrap, expired/revoked sessions, đổi password, lock/expiry/IP limit |
| Authorization | 34 PASS | Bảy role × mọi endpoint/method; unknown route deny; 22 report code; ownership/impersonation |
| Account/security HTTP | 51 PASS | CSRF, fixation/replay, status/role/password revocation, injection, XSS, mass assignment, reauth, admin race, CLI, cookie/headers/HTTPS, business HTTP regression |
| Security storage | 2 PASS | Unique partial index, TTL definition, atomic reservation và shared lock |
| MongoDB thật | 3 PASS | Unique partial index, kiểm tra expiry trước TTL cleanup, 80 concurrent reservations, race ADMIN cuối |
| **Tổng Pytest** | **120 PASS, 0 FAIL, 0 SKIP** | Lượt chạy toàn bộ suite với MongoDB thử nghiệm có xác thực |
| Docker image / Compose | PASS | Build Python 3.12-slim; hai Compose validate; chạy Gunicorn không dùng root |
| Gunicorn / shared session | PASS | Hai container độc lập, mỗi container hai worker; 32 request song song; logout và replay giữa container |
| Database credential | PASS | User ứng dụng không đọc được database khác |
| Trình duyệt desktop/mobile | PASS | Edge headless 1440×1000, 390×844; login, admin, customer, form, menu/logout; không tràn ngang |
| Static checks | PASS | Python compileall, node --check ba JS, git diff --check |

Tên từng test và PASS/FAIL: [SECURITY_TESTS.md](SECURITY_TESTS.md).
Kết quả máy đọc được: [security-test-results.xml](security-test-results.xml).
Ảnh kiểm chứng: [desktop login](security-ui/desktop-login.png),
[desktop accounts](security-ui/desktop-admin-0.png), [mobile create account](security-ui/mobile-admin-1.png),
[mobile customer profile](security-ui/mobile-customer-0.png). Tổng cộng 12 ảnh UI.

Mongomock trên Python 3.13 có cảnh báo datetime.utcnow từ dependency; không có test thất bại.
Mật khẩu kiểm thử được tạo ngẫu nhiên trong bộ nhớ hoặc chỉ nằm trong test fixture, không seed production.

## Ma trận quyền, route, schema và demo

- [Ma trận permission × role đầy đủ](RBAC_MATRIX.md).
- [Tất cả route/method và permission, cùng chính sách từng mã CB01–CB12/NC01–NC10](SECURITY_ROUTES.md).
- [Schema, indexes, cookie/session, bootstrap ADMIN và hướng dẫn demo từng role](SECURITY.md).
- [Tên và định nghĩa indexes MongoDB](SECURITY_INDEXES.md).
- [Audit ban đầu và baseline](SECURITY_AUDIT.md).

Khởi tạo ADMIN bằng `python -m flask --app app:create_app bootstrap-admin`, nhập email/password
tương tác; sau đó vào `/login`. Docker dùng `docker compose exec app` trước lệnh tương ứng.
Không có tài khoản mặc định, đăng ký công khai hoặc password gửi qua email.

## Rủi ro / phần chưa kiểm chứng

1. Chưa kiểm tra certificate, reverse proxy và cấu hình network trên hạ tầng production của người dùng.
   Cookie/HTTPS enforcement đã có test production flag; runtime Docker kiểm tra development HTTP.
2. Nếu worker chết khi giữ khóa mutation user, operator cần phục hồi sau khi dừng tất cả writer.
   Khóa không lease để tránh race/split-brain; đánh đổi khả năng sẵn sàng đã được ghi rõ.
3. Trên MongoDB standalone, mutation và audit không nằm trong transaction nhiều document;
   crash/DB outage đúng giữa hai thao tác có thể cần đối soát. Cần backup, giám sát và hạn chế truy cập DB trực tiếp.
4. Kiểm thử UI chỉ bao phủ Edge và hai viewport; không bao phủ mọi thiết bị/trình duyệt.
5. Production cần secret riêng và database credential đúng phạm vi. Volume MongoDB cũ cần
   operator provision credential trước khi bật --auth; không xóa volume để xử lý lỗi khởi tạo.

## File đã tạo/chỉnh sửa và lý do

<!-- FILE_LIST -->

| File | Reason |
|---|---|
| `.dockerignore` | Keep the verification virtual environment out of image build context. |
| `.env.example` | Provide explicit environment and secret/credential settings without defaults. |
| `.gitignore` | Exclude isolated local verification environment. |
| `Dockerfile` | Use readiness endpoint compatible with protected routes. |
| `README.md` | Link current security setup and replace obsolete anonymous/test guidance. |
| `app.py` | Initialize security, validate production config, register auth/CLI and error envelopes. |
| `config.py` | Environment, secure cookies, request/form size limits; remove default secret. |
| `db/docker-init-user.js` | Provision database-scoped credential on empty Docker data directories only. |
| `db/mongo.py` | Use current Flask application database for independent apps/workers. |
| `docker-compose.yml` | Single authenticated replica-set stack for management and shopping, web port 5002; alternate Compose files removed. |
| `docker-compose.yml` | Enable MongoDB authentication, scoped app user, required secrets/environment. |
| `docs/IMPLEMENTATION_REPORT.md` | Audit, policies, schema/indexes, operating instructions or recorded verification evidence. |
| `docs/RBAC_MATRIX.md` | Audit, policies, schema/indexes, operating instructions or recorded verification evidence. |
| `docs/SCHEMA.md` | Document separation of customer profiles and authentication collections. |
| `docs/SECURITY.md` | Audit, policies, schema/indexes, operating instructions or recorded verification evidence. |
| `docs/SECURITY_AUDIT.md` | Audit, policies, schema/indexes, operating instructions or recorded verification evidence. |
| `docs/SECURITY_INDEXES.md` | Audit, policies, schema/indexes, operating instructions or recorded verification evidence. |
| `docs/SECURITY_ROUTES.md` | Audit, policies, schema/indexes, operating instructions or recorded verification evidence. |
| `docs/SECURITY_TESTS.md` | Audit, policies, schema/indexes, operating instructions or recorded verification evidence. |
| `docs/security-test-results.xml` | Audit, policies, schema/indexes, operating instructions or recorded verification evidence. |
| `docs/security-ui/desktop-admin-0.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/desktop-admin-1.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/desktop-customer-0.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/desktop-customer-1.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/desktop-customer-2.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/desktop-login.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/mobile-admin-0.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/mobile-admin-1.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/mobile-customer-0.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/mobile-customer-1.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/mobile-customer-2.png` | Desktop/mobile browser evidence using isolated test data. |
| `docs/security-ui/mobile-login.png` | Desktop/mobile browser evidence using isolated test data. |
| `repositories/customer_repository.py` | Escape search input or validate review query filters. |
| `repositories/product_repository.py` | Escape search input or validate review query filters. |
| `repositories/public_repository.py` | Explicit active-product/approved-review projections without customer identifiers. |
| `repositories/review_repository.py` | Escape search input or validate review query filters. |
| `repositories/security_repository.py` | MongoDB indexes, atomic counters, session revocation and durable user-mutation lock. |
| `requirements.txt` | Add maintained Argon2id implementation. |
| `routes/api_routes.py` | Connect trusted principal and centralized policies to existing/new HTTP handlers. |
| `routes/auth_routes.py` | Connect trusted principal and centralized policies to existing/new HTTP handlers. |
| `routes/web_routes.py` | Connect trusted principal and centralized policies to existing/new HTTP handlers. |
| `scripts/export_security_policy.py` | Reproducible policy export or isolated runtime/browser verification. |
| `scripts/verify_database.py` | Do not print credential-bearing MongoDB URI. |
| `scripts/verify_security_browser.py` | Reproducible policy export or isolated runtime/browser verification. |
| `scripts/verify_security_runtime.py` | Reproducible policy export or isolated runtime/browser verification. |
| `services/access_policy.py` | Single ROLE_PERMISSIONS source, ownership rules and report policy. |
| `services/auth_service.py` | Argon2id, login/lockouts, server-side sessions, revocation, bootstrap and audit. |
| `services/customer_account_service.py` | Object-authorized profile, order and review access using principal customerCode. |
| `services/customer_service.py` | Whitelist/type validation, ownership, revocation or safe validation errors while retaining business logic. |
| `services/dashboard_service.py` | Exclude NC04/NC10 customer details from analyst responses. |
| `services/helpers.py` | Whitelist/type validation, ownership, revocation or safe validation errors while retaining business logic. |
| `services/order_service.py` | Whitelist/type validation, ownership, revocation or safe validation errors while retaining business logic. |
| `services/product_service.py` | Whitelist/type validation, ownership, revocation or safe validation errors while retaining business logic. |
| `services/promotion_service.py` | Whitelist/type validation, ownership, revocation or safe validation errors while retaining business logic. |
| `services/review_service.py` | Whitelist/type validation, ownership, revocation or safe validation errors while retaining business logic. |
| `services/security.py` | Deny-by-default route/method registry, authentication, CSRF, headers and errors. |
| `services/user_service.py` | Account administration, reauthentication and concurrent last-ADMIN protection. |
| `static/css/app.css` | Constrain responsive account dropdown width. |
| `static/js/app.js` | Attach synchronizer CSRF header only to same-origin AJAX mutations. |
| `templates/auth/account.html` | Vietnamese authentication, admin accounts, public catalog or customer self-service UI. |
| `templates/auth/catalog.html` | Vietnamese authentication, admin accounts, public catalog or customer self-service UI. |
| `templates/auth/login.html` | Vietnamese authentication, admin accounts, public catalog or customer self-service UI. |
| `templates/auth/orders.html` | Vietnamese authentication, admin accounts, public catalog or customer self-service UI. |
| `templates/auth/password.html` | Vietnamese authentication, admin accounts, public catalog or customer self-service UI. |
| `templates/auth/public_product.html` | Vietnamese authentication, admin accounts, public catalog or customer self-service UI. |
| `templates/auth/reviews.html` | Vietnamese authentication, admin accounts, public catalog or customer self-service UI. |
| `templates/auth/user_form.html` | Vietnamese authentication, admin accounts, public catalog or customer self-service UI. |
| `templates/auth/users.html` | Vietnamese authentication, admin accounts, public catalog or customer self-service UI. |
| `templates/base.html` | CSRF fields, permission-aware controls, privacy or customer-owned navigation. |
| `templates/customers/form.html` | CSRF fields, permission-aware controls, privacy or customer-owned navigation. |
| `templates/orders/detail.html` | CSRF fields, permission-aware controls, privacy or customer-owned navigation. |
| `templates/products/detail.html` | CSRF fields, permission-aware controls, privacy or customer-owned navigation. |
| `templates/products/form.html` | CSRF fields, permission-aware controls, privacy or customer-owned navigation. |
| `templates/products/list.html` | CSRF fields, permission-aware controls, privacy or customer-owned navigation. |
| `templates/promotions/form.html` | CSRF fields, permission-aware controls, privacy or customer-owned navigation. |
| `templates/reviews/list.html` | CSRF fields, permission-aware controls, privacy or customer-owned navigation. |
| `tests/conftest.py` | Authenticated regression fixtures and authentication/authorization/security integration coverage. |
| `tests/test_account_security.py` | Authenticated regression fixtures and authentication/authorization/security integration coverage. |
| `tests/test_auth_service.py` | Authenticated regression fixtures and authentication/authorization/security integration coverage. |
| `tests/test_authorization.py` | Authenticated regression fixtures and authentication/authorization/security integration coverage. |
| `tests/test_real_mongo.py` | Authenticated regression fixtures and authentication/authorization/security integration coverage. |
| `tests/test_security_storage.py` | Authenticated regression fixtures and authentication/authorization/security integration coverage. |
