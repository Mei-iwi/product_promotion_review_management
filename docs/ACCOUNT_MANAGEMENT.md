# Admin và Quản trị viên tài khoản

Phần mở rộng tích hợp với hệ thống RBAC, session MongoDB, Argon2id, CSRF và audit hiện có.
Không thay đổi dữ liệu tài khoản hiện hữu, schema/index unique, bootstrap hoặc quyền nghiệp vụ của nhân viên.

| Chức năng | ADMIN | ACCOUNT_MANAGER — Quản trị viên tài khoản |
|---|---|---|
| Xem/tìm/lọc/phân trang tài khoản | Tất cả | Chỉ CUSTOMER |
| Tạo tài khoản | Mọi vai trò hợp lệ | Máy chủ ấn định CUSTOMER |
| Đổi vai trò, cấp/thu hồi ACCOUNT_MANAGER | Có | Không |
| Đổi customerCode của tài khoản hiện hữu | Có; liên kết mới phải active và chưa được dùng | Không, kể cả gửi lại mã hiện tại |
| Vô hiệu hóa/kích hoạt/mở khóa | Tất cả; bảo vệ ADMIN cuối | Chỉ CUSTOMER |
| Khóa tạm thời thủ công | Có | Không |
| Đặt lại mật khẩu | Tất cả | Chỉ CUSTOMER |
| Đổi mật khẩu cá nhân, đăng xuất | Có | Có |
| Quyền sản phẩm/khuyến mãi/khách hàng/đơn/báo cáo | Theo ma trận ADMIN | Không; chỉ đọc danh mục công khai |

## Sử dụng Web

1. ADMIN vào **Tài khoản → Quản lý tài khoản → Tạo tài khoản**, chọn **Quản trị viên tài khoản**.
2. Nhập email, mật khẩu ban đầu (8–128 ký tự) và mật khẩu của ADMIN trong ô xác thực lại.
   Không nhập customerCode cho tài khoản nhân viên.
3. Sau đăng nhập, mọi vai trò đều vào `/catalog`. ACCOUNT_MANAGER mở tab **Quản lý tài khoản** để vào `/admin/users`.
4. Danh sách chỉ có CUSTOMER; tìm theo một phần email, lọc trạng thái, chọn số dòng mỗi trang.
   Với ADMIN có thêm bộ lọc vai trò. Trang trước/sau giữ nguyên các bộ lọc.
5. Khi tạo CUSTOMER, nhập customerCode của hồ sơ có thật và đang hoạt động. Không có hồ sơ?
   ADMIN hoặc SUPPORT_STAFF phải tạo hồ sơ khách hàng theo luồng nghiệp vụ trước.
6. Trong **Quản lý / Đặt lại mật khẩu**, chọn trạng thái “Vô hiệu hóa” để ngừng truy cập;
   chọn “Đang hoạt động” để kích hoạt/mở khóa. Không có chức năng xóa tài khoản.
7. Để đặt lại mật khẩu, nhập mật khẩu mới. Để trống nếu giữ nguyên. Trình duyệt yêu cầu
   xác nhận khi vô hiệu hóa hoặc đặt lại mật khẩu. Mọi mutation vẫn cần CSRF ở server.

Form lỗi validation hiển thị tiếng Việt và giữ email/vai trò/trạng thái/mã khách hàng hợp lệ;
cả password và actorPassword luôn trống khi render lại. Thông báo thành công dùng flash tiếng Việt.
Các trạng thái dữ liệu vẫn là active/disabled/locked, giao diện dùng nhãn tiếng Việt.

## Web/API dùng chung phạm vi

- Các URL và permission theo method không đổi. Có thêm hai permission phạm vi:
  `users.manage_all` cho ADMIN, `users.manage_customers` cho ACCOUNT_MANAGER.
- Truy vấn danh sách **và count_documents** của ACCOUNT_MANAGER có `role: CUSTOMER`,
  trước khi sort/skip/limit. Không đọc tất cả rồi lọc trong Python/Jinja.
- `managed_user` là chính sách đích chung của Web GET/POST và API PUT. Tài khoản không tồn tại,
  ID sai hoặc ngoài phạm vi đều trả 404. Client không được suy luận tài khoản ngoài phạm vi.
- Trong `user_mutation_lock`, service đọc lại actor, kiểm tra status/authVersion và permission;
  sau đó đọc lại target bằng truy vấn có phạm vi. Nếu quyền hoặc role đích đã đổi thì từ chối.
- ACCOUNT_MANAGER tạo CUSTOMER khi không gửi role hoặc gửi đúng CUSTOMER; gửi role khác trả 403.
  Khi cập nhật, chỉ cần xuất hiện trường `role` hoặc `customerCode` cũng trả 403, kể cả giá trị không đổi.
  Gửi status=locked cũng bị từ chối. Các trường ngoài allowlist hoặc sai kiểu trả 400.
- Chỉ ADMIN có quyền gán role; ACCOUNT_MANAGER không được sửa chính mình qua quản trị tài khoản
  nhưng vẫn đổi mật khẩu cá nhân và đăng xuất qua các route tài khoản riêng.

## Hợp đồng GET /api/users

Response giữ nguyên `{success, message, data}`, trong đó **data vẫn là mảng** tài khoản an toàn.
Không gửi page/per_page thì trả toàn bộ kết quả trong phạm vi đã lọc, tương thích client cũ.
Khi gửi page/per_page, data vẫn là mảng, chỉ gồm trang được yêu cầu.

| Query parameter | Quy tắc |
|---|---|
| q | Chuỗi tối đa 254 ký tự; tìm một phần email chuẩn hóa; escape regex, không nhận Mongo operator |
| role | Rỗng hoặc mã role hợp lệ; ACCOUNT_MANAGER chỉ được yêu cầu CUSTOMER |
| status | Rỗng hoặc active/disabled/locked |
| page | Số nguyên 1–100000; mặc định 1 |
| per_page | Số nguyên 1–100; mặc định 10 |

Tham số ngoài danh sách, tham số lặp, kiểu không phải chuỗi và giá trị sai giới hạn bị từ chối 400.
Không nhận trường sort từ client; sắp xếp cố định `emailNormalized ASC, _id ASC` để phân trang ổn định.
Header `X-Total-Count` luôn là tổng sau khi áp phạm vi và bộ lọc. Khi phân trang, thêm `X-Page`, `X-Per-Page`.
Ví dụ: `/api/users?q=example&status=active&page=2&per_page=10`.

## Xác thực lại, thu hồi phiên và audit

- Tạo ADMIN/ACCOUNT_MANAGER, cấp hoặc thu hồi các vai trò này cần actorPassword hiện tại.
- Thay đổi vai trò/trạng thái hoặc reset password của nhân viên đặc quyền cần xác thực lại.
  Chỉnh ADMIN/ACCOUNT_MANAGER luôn yêu cầu actorPassword. CUSTOMER thông thường không yêu cầu actorPassword.
- Đổi role/status/password tăng authVersion và gọi revoke_user. Cookie cũ bị từ chối ở request kế tiếp,
  kể cả kích hoạt lại tài khoản. Mở khóa còn xóa counter lỗi đăng nhập theo email; không xóa rate limit IP.
- Update ghi actor/target, old/new role, old/new status, old/new customerCode, cờ passwordReset.
  Không ghi password/actorPassword/hash/token. Không đưa bí mật vào response hoặc form lỗi.
- Bảo vệ ADMIN active cuối tiếp tục nằm trong cùng khóa cập nhật MongoDB. Không dùng count-then-update
  bên ngoài khóa, không có xóa user hoặc xóa dữ liệu để phục hồi quyền.
- Không cần migration tài khoản MongoDB hiện hữu; khi deploy cần restart worker để nạp policy mới.

## Kiểm thử

Các tệp tạo/chỉnh sửa trong phần mở rộng này (tích hợp trên working tree hiện có):

| Tệp | Thay đổi |
|---|---|
| services/access_policy.py | ACCOUNT_MANAGER, permission phạm vi, nhãn tiếng Việt và landing |
| services/auth_service.py | Tạo CUSTOMER theo phạm vi actor mới nhất, reauth khi tạo ADMIN/ACCOUNT_MANAGER trong khóa |
| services/user_service.py | Chính sách actor/target chung, lọc/phân trang, reauth, cập nhật/audit/revoke và mở khóa |
| repositories/user_repository.py | Truy vấn/count/sort/skip/limit có phạm vi; projection loại bí mật |
| services/security.py | Đưa nhãn vai trò/trạng thái vào context Jinja; giữ nguyên CSRF và endpoint registry |
| routes/auth_routes.py | Kết nối Web/API với service có phạm vi, giữ array contract và form lỗi |
| templates/auth/users.html | Bộ lọc, tổng phù hợp, phân trang và thao tác theo quyền |
| templates/auth/user_form.html | Vai trò/liên kết chỉ đọc cho manager, giữ giá trị và xóa ô mật khẩu khi lỗi |
| templates/base.html | Hiển thị tên vai trò tiếng Việt trong menu tài khoản |
| static/js/app.js | Xác nhận khi vô hiệu hóa/reset; hủy xác nhận không vô hiệu nút submit |
| tests/conftest.py | Fixture ACCOUNT_MANAGER, chuẩn hóa email khi dùng lại tài khoản |
| tests/test_account_security.py | Vòng đời tài khoản, validation, pagination/filter, reauth, sessions, race, audit và form |
| tests/test_authorization.py | Ma trận thêm vai trò mới, phạm vi Web/API và chặn cấp quyền/liên kết trái phép |
| scripts/export_security_policy.py | Xuất matrix/route có mô tả object scope và chọn bằng chứng test mới nhất |
| scripts/verify_security_browser.py | Kiểm tra manager, xác nhận/hủy và desktop/mobile trên dữ liệu mock |
| README.md, docs/SECURITY.md | Hướng dẫn vai trò và liên kết tài liệu mới |
| docs/RBAC_MATRIX.md, docs/SECURITY_ROUTES.md | Ma trận và route/permission/phạm vi cập nhật |
| docs/ACCOUNT_MANAGEMENT.md | Hướng dẫn chức năng, API, kiểm thử và giới hạn xác minh |
| docs/SECURITY_TESTS.md, docs/account-management-test-results.xml | Bằng chứng test hiện hành |
| docs/security-ui/*.png | Ảnh UI được cập nhật, thêm ảnh manager desktop/mobile |

Trong Git Bash:

```bash
source .venv/Scripts/activate
python -m pytest -q
```

Các test mới mở rộng tests/test_account_security.py, tests/test_authorization.py và fixture hiện có:
vòng đời ACCOUNT_MANAGER, chặn truy cập chéo bằng URL/API, CUSTOMER liên kết active/unique,
CSRF, reauth, pagination/filter/array contract, giữ form/clear password, session revocation/replay,
kiểm tra lại actor/target trong khóa, audit không chứa bí mật và race ADMIN cuối.
Ba test MongoDB thật dùng fixture opt-in và được skip nếu thiếu SECURITY_TEST_MONGO_URI;
`scripts/verify_security_runtime.py` tạo môi trường Docker riêng để chạy cả ba test này.

Kết quả lần triển khai này: **176 PASS, 3 SKIP**; không có test FAIL. Ba SKIP là các test
MongoDB thật cần URI thử nghiệm riêng, không bị bỏ qua authentication/authorization/CSRF.
Bằng chứng đầy đủ: [account-management-test-results.xml](account-management-test-results.xml),
[SECURITY_TESTS.md](SECURITY_TESTS.md). Baseline trước thay đổi: 122 PASS, 3 SKIP.

Edge headless đã kiểm tra desktop 1440×1000 và mobile 390×844: login/landing của ACCOUNT_MANAGER,
danh sách chỉ CUSTOMER, biểu mẫu không có ô gán role/đổi liên kết, hộp xác nhận vô hiệu hóa/reset,
hủy xác nhận vẫn giữ nút submit hoạt động, logout và không tràn ngang.
Ảnh: [desktop manager](security-ui/desktop-manager-0.png),
[mobile manager](security-ui/mobile-manager-0.png),
[mobile edit](security-ui/mobile-manager-edit.png).

Chưa chạy lại integration MongoDB thật/Docker cho phần mở rộng này; môi trường dữ liệu đang dùng
không bị thay đổi. Cảnh báo kiểm thử hiện có đến từ datetime.utcnow trong Mongomock và quyền ghi
cache Pytest, không ảnh hưởng kết quả. Không commit/push hoặc tự cấp ACCOUNT_MANAGER cho tài khoản thật.
