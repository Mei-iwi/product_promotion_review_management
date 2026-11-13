# Hồ sơ cá nhân, avatar và bảo mật tài khoản

> Đã mở rộng hồ sơ cho tất cả vai trò; chi tiết quyền và storage staff mới tại [STAFF_PROFILES.md](STAFF_PROFILES.md). Phần dưới ghi lại triển khai hồ sơ CUSTOMER ban đầu.

Triển khai và xác minh ngày 13/11/2026 (Asia/Saigon), trực tiếp trên ứng dụng Flask/Jinja/MongoDB hiện hữu.

## Kết quả

`/account` có header avatar tròn 112px, họ tên, email đăng nhập từ users, hạng thành viên và ba nhóm biểu mẫu độc lập: thông tin cá nhân, avatar, bảo mật. Giao diện Mint & Lavender dùng lại tokens hiện có, hai cột desktop/một cột mobile. Không đưa lại thanh điều hướng tài khoản đã được yêu cầu xóa.

Không render customerCode ra HTML, hidden input, tooltip hay data attribute. Quyền và đối tượng được lấy từ session server; không đổi liên kết users/customers/carts/orders/reviews. Email đăng nhập và hạng chỉ đọc, không có name để gửi qua form. customers.email vẫn là email nghiệp vụ cũ, không được endpoint hồ sơ chỉnh sửa.

## Audit và tái sử dụng

- `auth_service.change_password()` đã có Argon2id, xác thực mật khẩu hiện tại, validate_password, user_mutation_lock, tăng authVersion và revoke_user. Giữ nguyên toàn bộ file service này; route chỉ thêm kiểm tra confirmPassword và xử lý UI/flash/cookie.
- Profile cũ chỉ sửa họ tên/địa chỉ, yêu cầu họ tên kể cả khi cập nhật từng trường; lỗi render trang chung. Đã thêm validation sáu trường, semantics cập nhật từng trường và lỗi ngay trên form.
- Ảnh trước đây chưa có nơi lưu runtime. Đã thêm service ảnh riêng, lưu ngoài static, dùng volume Docker thuộc appuser. Pillow chuyển từ dependency dev sang runtime, giữ phiên bản dự án đang dùng.
- Form quản trị khách hàng vốn dùng $set, nên các field profile/avatar mới không bị mất khi quản trị cập nhật thông tin cũ; có test xác nhận.
- Checkout vốn có đối tượng values riêng. Chỉ thêm mặc định phone từ hồ sơ nếu chưa có values; không ghi đè số điện thoại/địa chỉ đang nhập, quote hay thông tin đơn cũ.

## Quy ước dữ liệu

| Trường | Validation/lưu trữ |
|---|---|
| fullName | Chuỗi bắt buộc, trim, tối đa 200 ký tự. Bỏ qua trường trong request thì giữ tên hiện tại; gửi rỗng bị từ chối. |
| phone | Tùy chọn. Số Việt Nam: mobile 0[35789] + 8 số, cố định 02 + 9 số; chấp nhận +84 thay 0. Loại bỏ khoảng trắng/dấu phân cách thông dụng. |
| dateOfBirth | Tùy chọn, chuỗi ISO YYYY-MM-DD, ngày thật, không sau ngày hiện tại tại Việt Nam. |
| gender | Tùy chọn: male/female/other/undisclosed. |
| address | Tùy chọn, trim, tối đa 500 ký tự. |
| bio | Tùy chọn, trim, tối đa 300 ký tự. |
| avatar | Object metadata: key ngẫu nhiên, mediaType, width, height, updatedAt UTC. Không lưu binary. |

Trường không gửi được giữ nguyên. Trường tùy chọn gửi rỗng/whitespace bị $unset. Chỉ ghi field đã gửi bằng $set/$unset, không thay document. Giá trị null/object/list hoặc field ngoài allowlist bị từ chối. Không cho gán email/role/level/status/customerCode/passwordHash/authVersion/avatar qua profile endpoint.

Thông tin cá nhân và avatar dùng lại quyền customers.read_own / customers.update_own_profile, không mở quyền mới cho staff. Trước khi ghi, service giữ user_mutation_lock và đọc lại user/authVersion/trạng thái/customer link. Các service quản lý tài khoản hiện hữu vẫn dùng cùng khóa; Argon2id và ma trận RBAC không đổi.

## API và form

| Endpoint | Method | Permission / hành vi |
|---|---|---|
| /account | GET | customers.read_own; trang hồ sơ. |
| /account/profile | POST | customers.update_own_profile; form thông tin cá nhân. |
| /api/account/profile | GET / PUT | Hợp đồng hiện hữu; đọc/sửa hồ sơ của session. PUT chấp nhận cập nhật từng trường. |
| /account/avatar | GET | customers.read_own; chỉ trả avatar của phiên hiện tại hoặc default SVG do ứng dụng cung cấp. Không nhận key/path/customer ID. |
| /account/avatar | POST | customers.update_own_profile + CSRF; multipart đúng một file avatar. |
| /account/avatar/delete | POST | customers.update_own_profile + CSRF; không nhận trường chỉ định người dùng/file. |
| /account/change-password | GET / POST | account.change_own_password như cũ. POST bắt buộc currentPassword/newPassword/confirmPassword; giữ URL cho mọi vai trò. |

Các form web với Accept: application/json nhận envelope success/message/data, cho phép frontend gửi từng form riêng. Lỗi một form không điều hướng trang hay xóa bản nháp của form khác. Password bị xóa khỏi input sau lỗi server; không được điền lại từ server, trả trong JSON, ghi log/audit, query string hoặc browser storage. Nếu gửi HTML thông thường, route vẫn render lỗi form/redirect phù hợp; preview và bảo toàn bản nháp giữa các form dùng JavaScript.

Frontend xác nhận mật khẩu khớp và khác mật khẩu hiện tại; backend xác nhận lại rồi gọi đúng service change_password hiện hữu. Đổi thành công xóa auth cookie, thu hồi toàn bộ session, về /login và flash thông báo thành công. Không tự đăng nhập lại.

## Xử lý ảnh và tính nhất quán

- Chỉ JPEG/PNG/WebP tĩnh; kiểm tra đuôi hợp lệ và format thực bằng Pillow, verify rồi decode lại. Từ chối SVG/executable/ảnh giả, ảnh lỗi, animation, file >800 KiB, >16 triệu pixel, >8192px mỗi cạnh và decompression bomb của Pillow.
- EXIF orientation được áp trước resize. Ảnh giữ tỷ lệ, tối đa 512×512, compositing trên canvas RGB mới và xuất WebP; không mang EXIF, ICC/comments hay tên gốc sang file mới.
- Tên 64 hex ngẫu nhiên + .webp; đường dẫn chỉ do service tạo, kiểm tra key/parent/symlink. Filename upload có path/drive/null bị từ chối. Không expose thư mục upload dưới static.
- Ghi file tạm bằng chế độ tạo file mới, flush/fsync và os.replace; file tạm được dọn. Sau khi file mới ghi xong mới cập nhật MongoDB; chỉ sau cập nhật thành công mới xóa file cũ.
- Nếu MongoDB báo lỗi sau commit, service đọc lại trước khi xóa file mới. Khi không xác định được kết quả commit, giữ file để tránh xóa một ảnh đã được tham chiếu. Crash hoặc lỗi xóa file có thể để lại orphan an toàn; có CLI đối soát, không tự xóa file đang được tham chiếu.
- GET riêng tư yêu cầu session, không nhận key/file path; Content-Type cố định, nosniff và no-store hiện hữu. Reference hỏng/file mất trả default thay vì lộ đường dẫn.

## Docker, backup và cleanup

Compose mount volume `avatar_data` tại `/app/instance/avatars`; Dockerfile tạo/chown thư mục trước khi chuyển USER appuser. `AVATAR_STORAGE_DIR` được cấu hình vào đúng mount. Local mặc định `instance/avatars`; thư mục này và `.test-tmp/` bị loại khỏi Git và Docker build context.

Đã build stack tạm bằng credential/DB/volume ngẫu nhiên, upload ảnh qua HTTP, force-recreate container app thật rồi xác nhận SHA-256 của ảnh không đổi, dữ liệu hồ sơ và session vẫn tồn tại. Đã xác minh UID không phải root, file thuộc UID appuser và thư mục đọc/ghi được. Stack tạm đã được script dọn bằng project riêng; không dùng volume hay DB hiện có của người dùng.

Rebuild app để nhận code/dependency mới, không xóa volume:

```powershell
docker compose up --build -d app
```

Local dùng `.venv` đã cài requirements và chạy app.py như trước. Khi backup, lưu đồng thời MongoDB và volume avatar_data; giữ nguyên storage key khi restore. Recreate app giữ volume, còn xóa volume sẽ xóa file upload.

Dọn file orphan trên môi trường chủ động bảo trì:

```powershell
# Dry-run mặc định, không xóa file
python -m flask --app app:create_app cleanup-avatar-orphans
# Chỉ xóa file sinh bởi service, không được DB tham chiếu, đã hơn 24 giờ
python -m flask --app app:create_app cleanup-avatar-orphans --apply
```

Lệnh giữ cùng account lock, bỏ qua symlink và file lạ. Không tự xóa lock bị bỏ lại sau crash; quy trình operator hiện hữu vẫn áp dụng.

## Tệp thay đổi trong hạng mục hồ sơ

| Tệp | Nội dung |
|---|---|
| services/customer_account_service.py | Validation, cập nhật từng field, fresh ownership/account checks dưới lock. |
| services/avatar_service.py | Service ảnh chuẩn hóa, private storage, commit/cleanup an toàn và CLI orphan. |
| routes/auth_routes.py | Form profile, avatar GET/POST/delete, confirmPassword, lỗi/flash và AJAX envelope. |
| routes/shopping_routes.py | Điền sẵn phone khi chưa có recipient draft. |
| services/security.py | Registry ba endpoint avatar, dùng permission hiện hữu. |
| app.py | Đăng ký CLI avatar cleanup. |
| config.py | Cấu hình AVATAR_STORAGE_DIR. |
| requirements.txt / requirements-dev.txt | Pillow thuộc runtime. |
| Dockerfile / docker-compose.yml | Thư mục appuser, environment và named volume avatar_data. |
| .gitignore / .dockerignore | Không lưu/copy runtime uploads hay thư mục test tạm. |
| templates/auth/account.html | Header/avatar, thông tin và bảo mật dạng section; không customerCode. |
| templates/auth/_password_form.html | Partial ba password input dùng chung, CSRF và toggle accessible. |
| templates/auth/password.html | Giữ trang riêng tương thích cho mọi role được phép. |
| static/js/account.js | Preview có xác nhận, request độc lập, trạng thái lỗi/thành công, giữ draft và kiểm tra confirm. |
| static/js/app.js | Toggle password giữ nhãn riêng cho từng trường; CSRF fetch wrapper giữ nguyên. |
| static/css/app.css | Profile header/sections, avatar 112px, responsive và status. |
| static/img/avatar-default.svg | Avatar mặc định do app cung cấp, không chấp nhận SVG upload. |
| tests/test_profile_avatar.py | 51 test hồ sơ/avatar, validation, scope, CSRF, metadata, giới hạn, lỗi commit/storage, cleanup và admin regression. |
| tests/test_password_profile.py | 11 test password/profile integration, revoke, no-leak, staff compatibility, checkout prefill. |
| tests/test_account_security.py | Payload test đổi mật khẩu hiện hữu thêm confirmPassword bắt buộc; giữ kiểm tra thu hồi phiên. |
| scripts/verify_profile_browser.py | Edge UI test với DB trong bộ nhớ, session và CSRF thật. |
| scripts/verify_profile_compose.py | Isolated Docker/MongoDB HTTP integration, recreate persistence, password/session. |
| README.md / docs/SCHEMA.md / docs/SECURITY_ROUTES.md / docs/PROFILE.md | Tài liệu schema, quyền, triển khai, lưu trữ và bằng chứng. |

Không sửa auth_service.py, access_policy.py, customer_repository.py hay cơ chế hash/session/CRUD quản trị hiện hữu. Không commit/push/deploy lại stack thật.

## Kiểm thử và bằng chứng

Dùng Python của `.venv`, pytest test-only DB, không production DB.

| Kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q -p no:cacheprovider --basetemp=.test-tmp/regression-final --junitxml=docs/profile-test-results.xml` | **301 PASS, 15 SKIP**. 15 opt-in test cần MongoDB thật được chạy riêng phía dưới. |
| `python scripts/verify_shopping_replica.py` | **15 PASS** MongoDB replica; Edge desktop/mobile mua hàng, áp/bỏ mã, quote, COD, xác nhận/hoàn tất, review và hủy đơn đều PASS. |
| `python scripts/verify_profile_browser.py` | **8 nhóm kịch bản PASS**, gồm 5 viewport 360/390/768/1024/1440, không page overflow, preview không tự upload, giữ draft khi lỗi, upload/xóa ảnh, form reset/reload, password match/visibility, revoke hai phiên và đăng nhập lại. |
| `python scripts/verify_profile_compose.py` | **5 nhóm xác minh PASS** trên Docker/MongoDB thật, gồm force-recreate avatar persistence và auth revocation. |
| `python -m compileall -q app.py config.py db repositories routes services scripts` | PASS. |
| `node --check static/js/app.js` | PASS. |
| `node --check static/js/account.js` | PASS. |
| `docker compose config --quiet` | PASS; kiểm tra cấu hình không in credential nội suy. |
| `git diff --check` | PASS. |

Có cảnh báo datetime.utcnow() của Mongomock. Pytest tạm dùng thư mục workspace riêng và tắt cache vì thư mục temp/cache Windows cũ gặp quyền truy cập; không đổi assertions hay bỏ test để vượt lỗi. Các lệnh Docker/browser cần quyền truy cập daemon/network đã chạy và có kết quả thực.

Bằng chứng: [unit/HTTP XML](profile-test-results.xml), [Docker JSON](profile-compose-results.json), [UI JSON](profile-ui/results.json), [replica XML](shopping-replica-results.xml), [desktop](profile-ui/1440-account.png), [mobile](profile-ui/360-account.png). Ảnh dùng hồ sơ và avatar tổng hợp phục vụ test.

Phần chưa xác minh: thiết bị thật, Safari/Firefox, screen reader, tải lớn và HA nhiều replica ứng dụng trên nhiều host. Local filesystem volume phù hợp triển khai Compose hiện tại; nhiều host cần storage dùng chung và cùng AVATAR_STORAGE_DIR. Không có thay đổi cần chờ xác nhận trong source; stack đang dùng của người dùng chưa được tự restart.
