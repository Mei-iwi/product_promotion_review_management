# Hồ sơ riêng cho ADMIN và nhân viên

Tất cả 8 vai trò đều mở **Tài khoản → Hồ sơ của tôi** hoặc `/account`. Các vai trò mới có hồ sơ: ADMIN, ACCOUNT_MANAGER, PRODUCT_STAFF, MARKETING_STAFF, SUPPORT_STAFF, REVIEW_MODERATOR và ANALYST.

## Chức năng và lưu trữ

- Họ tên, điện thoại, ngày sinh, giới tính, địa chỉ, giới thiệu; email đăng nhập và vai trò chỉ đọc.
- Chọn ảnh trực tiếp trên avatar, xem trước, xác nhận lưu, thay/xóa ảnh; dùng lại giới hạn/chuẩn hóa ảnh và private endpoint hiện có.
- Đổi mật khẩu trong trang hồ sơ, dùng nguyên auth_service.change_password và chính sách thu hồi tất cả phiên.
- Staff lưu field trong `users.profile`, avatar trong `users.profile.avatar`. CUSTOMER tiếp tục lưu tại `customers` và `customers.avatar`; không tạo customerCode hay khách hàng giả cho nhân viên.
- Tài khoản cũ chưa có profile mở được ngay, tên hiển thị tạm từ phần tên email cho tới khi lưu tên riêng. Không cần migration/import.
- Bố cục Mint & Lavender dùng chung, có vai trò thay hạng thành viên, không thêm lại các tab/nút/giải thích đã được yêu cầu bỏ.

## Quyền và sở hữu

Thêm `account.read_own_profile` / `account.update_own_profile` cho mọi vai trò, chỉ áp dụng hồ sơ và avatar của chính tài khoản. Không cấp các quyền CUSTOMER như giỏ, đơn riêng, review riêng hay quyền quản lý nghiệp vụ cho staff. Các endpoint web/API hồ sơ và avatar dùng hai quyền mới; các endpoint mua sắm tiếp tục dùng quyền cũ.

`account_profile_service.current_account` đọc lại user bằng session ID, xác nhận trạng thái, authVersion và permission. Mọi mutation giữ account lock; collection/query/field avatar đều được server xác định từ principal hiện hành, không nhận target từ request. API staff dùng allowlist để không trả passwordHash/authVersion/security fields. Role/email/status/customerCode/avatar không thể gán qua profile API.

`customer_account_service.validate_profile` được tái sử dụng để tránh hai bộ validation. Trường không gửi giữ nguyên; tùy chọn rỗng dùng $unset. Staff chỉ sửa dot paths `profile.<field>`, không thay toàn bộ user hay password/role/session.

Avatar dùng chung volume nhưng tham chiếu riêng từng tài khoản. Khi thay ảnh, commit file → Mongo reference → dọn file cũ; xử lý ambiguous commit giữ nguyên file có thể đã được tham chiếu. CLI cleanup quét cả customers.avatar và users.profile.avatar, không xóa avatar staff đang dùng, kể cả khi file đã cũ.

## Tệp thay đổi

| Tệp | Thay đổi |
|---|---|
| services/account_profile_service.py | Facade theo role, own-account validation, DTO staff, cập nhật users.profile và lựa chọn storage target. |
| services/customer_account_service.py | Tách validation để tái sử dụng; giữ lưu trữ/kiểm tra khách hàng cũ. |
| services/avatar_service.py | Dùng storage target theo user, giữ quy trình ảnh; cleanup cả hai collection. |
| services/access_policy.py | Hai quyền hồ sơ cá nhân; authorize_object chỉ cho user ID của chính principal. |
| services/security.py | Đăng ký quyền mới cho routes hồ sơ/avatar; không đổi quyền route nghiệp vụ. |
| routes/auth_routes.py | Gọi facade chung cho web/API hồ sơ. |
| templates/base.html | Hồ sơ của tôi cho mọi role, không còn mục đổi mật khẩu trùng lặp; profile dùng layout riêng. |
| templates/auth/account.html | Nhãn/badge vai trò cho staff, giữ hạng với CUSTOMER. |
| templates/auth/password.html | Liên kết quay về hồ sơ cho mọi role. |
| tests/test_staff_profiles.py | 21 test mới cho 7 role, own storage, field allowlist, partial update, CSRF, avatar isolation/cleanup và phiên cũ. |
| tests/test_profile_avatar.py | Điều chỉnh kỳ vọng ADMIN hiện có quyền avatar riêng, vẫn chặn upload thiếu file/CSRF. |
| tests/test_review_purchase.py | Cập nhật menu theo yêu cầu đã bỏ mục đổi mật khẩu, xác nhận password form nằm trong hồ sơ. |
| scripts/verify_staff_profile_browser.py | Edge checks cho cả 7 role và ảnh desktop/mobile. |
| scripts/verify_profile_compose.py | Kiểm tra avatar CUSTOMER/ADMIN lưu riêng và tồn tại sau force-recreate app. |
| README.md, docs/SCHEMA.md, docs/RBAC_MATRIX.md, docs/SECURITY_ROUTES.md | Tài liệu storage, quyền và hướng dẫn cập nhật. |

## Kiểm thử

- Suite hồi quy: **322 PASS, 15 SKIP**. Lệnh: `python -m pytest -q -p no:cacheprovider --basetemp=.test-tmp/staff-all-final --junitxml=docs/staff-profile-test-results.xml`.
- Nhóm profile/avatar/password: 83 PASS, gồm tất cả role; sau đó chạy suite đầy đủ để xác nhận các chức năng khác.
- `python scripts/verify_staff_profile_browser.py`: PASS 7 role, kiểm tra lưu/reload, role/email chỉ đọc, password form, không tràn ngang ở 390px/1440px. Có kiểm tra upload avatar qua browser cho ADMIN/ANALYST.
- `python scripts/verify_profile_compose.py`: PASS 5 nhóm kiểm tra MongoDB/Docker thật, giữ đồng thời ảnh ADMIN/CUSTOMER sau force-recreate, xóa ảnh khách hàng không mất ảnh staff, password/session vẫn đúng.
- Compileall, node --check app.js/account.js, docker compose config --quiet và git diff --check: PASS.

Tất cả dùng DB/volume test độc lập; không import/chỉnh DB hoặc restart stack hiện có của người dùng. Có cảnh báo datetime.utcnow() từ dependency Mongomock. 15 opt-in test trong suite thông thường cần MongoDB thật; báo cáo XML ghi SKIP trung thực. Các test giao dịch replica đã có script riêng và không bị bỏ hay sửa assertions cho hạng mục hồ sơ.

Bằng chứng: [suite XML](staff-profile-test-results.xml), [UI JSON](staff-profile-ui/results.json), [Docker JSON](profile-compose-results.json), [ảnh ADMIN](staff-profile-ui/admin-1440.png), [ảnh ANALYST mobile](staff-profile-ui/analyst-390.png).

## Cập nhật ứng dụng

Code đã được thêm trực tiếp. Nếu dùng Docker, build lại app với `docker compose up --build -d app`; giữ volume avatar_data hiện hữu. Không cần tạo lại users hay customers. Chưa tự deploy/restart stack thật. Safari/Firefox, screen reader và triển khai nhiều host chưa được xác minh trong lượt này.
