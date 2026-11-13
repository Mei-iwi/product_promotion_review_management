# Nâng cấp UI/UX Mint & Lavender

Ngày kiểm tra: 13/11/2026 (Asia/Saigon). Triển khai trực tiếp trên repository Flask/Jinja2/Bootstrap hiện hữu.

## A. Audit và quyết định thiết kế

- Navbar xanh đậm trước đây gom toàn bộ nghiệp vụ và mua sắm vào một hàng. Nay header trắng cho mua sắm, sidebar quản trị riêng từ permission thực tế của từng vai trò. Nhân viên chỉ nhìn thấy các nhóm được cấp quyền; không đổi role matrix hay landing sau đăng nhập.
- Các bộ lọc quản trị thiếu label, mất lựa chọn sau reload và phân trang sản phẩm làm mất query. Đã bổ sung label/reset, giữ giá trị và query; bộ lọc giá/nhãn được thu gọn, tự mở khi đang áp dụng.
- Form CRUD trước đây render lại dữ liệu cũ/trống sau validation error. Nay template đọc lại request.form, escape bằng Jinja; tên field, quy tắc validation và cách ghi dữ liệu không đổi.
- CSS trước đây thiên về navy/blue, focus ring vàng và bo góc nhỏ. Đã thay bằng hệ token Mint/Lavender, typography, spacing, shadow và radius dùng chung; không thêm thư viện UI hay font network.
- Submit handler cũ vô hiệu hóa một số button trước khi browser thu thập dữ liệu. Nay giữ button nguyên vẹn, chặn submit lặp ở cấp form, chỉ đổi nhãn sau xác nhận và khôi phục khi quay lại bằng Back.
- SVG trước đây scale nhãn quá nhỏ ở mobile và bảng dữ liệu bị ẩn hoàn toàn. Nay kích thước biểu đồ dựa theo vùng chứa, cuộn trong card khi cần, có tooltip và bảng số liệu mở được bằng bàn phím. API lỗi được phân biệt với không có dữ liệu và cô lập theo nhóm.
- Trang lỗi trước đây luôn dẫn về route tổng quan chỉ Admin được xem. Nay dùng landing hiện hữu và có đường về catalog.

## B. Tệp mã nguồn đã sửa/thêm

| Đường dẫn | Thay đổi và mục đích |
|---|---|
| `scripts/verify_mint_ui.py` | Kiểm tra Edge 5 viewport, keyboard/navigation, overflow, reduced motion và lỗi/rỗng dashboard trên dữ liệu bộ nhớ. |
| `static/css/app.css` | Design tokens, Bootstrap overrides, layout, card/form/table, responsive và reduced motion. |
| `static/img/logo.svg` | SVG logo/ảnh dự phòng đồng bộ Mint & Lavender; favicon không gọi route không tồn tại. |
| `static/img/product-placeholder.svg` | SVG logo/ảnh dự phòng đồng bộ Mint & Lavender; favicon không gọi route không tồn tại. |
| `static/js/app.js` | Giữ submitter nguyên vẹn, khóa gửi lặp, khôi phục khi Back, password toggle, fallback ảnh và vùng bảng dùng bàn phím; giữ CSRF fetch wrapper. |
| `static/js/dashboard.js` | Palette, SVG responsive, tooltip, bảng số liệu mở rộng, loading và lỗi riêng từng API. |
| `static/js/reports.js` | Giữ vùng bảng truy cập bằng bàn phím sau chuyển báo cáo AJAX; tránh lặp thông báo lỗi. |
| `templates/auth/account.html` | Account tabs theo quyền, badge/empty state/xác nhận thống nhất. |
| `templates/auth/cart.html` | Tiến trình mua hàng; kế thừa tổng tiền sticky, form và voucher styling dùng chung. |
| `templates/auth/catalog.html` | Hero, tìm kiếm/lọc, card ảnh/giá/rating/tồn kho và empty state; không tạo ưu đãi giả. |
| `templates/auth/checkout.html` | Tiến trình, dấu bắt buộc, summary sticky và lời hướng dẫn; giữ action/CSRF/quote/formaction/formnovalidate. |
| `templates/auth/login.html` | Form trung tâm, bố cục giới thiệu, giữ email sau lỗi, nút hiện/ẩn mật khẩu và autocomplete. |
| `templates/auth/order_confirmation.html` | Account tabs theo quyền, badge/empty state/xác nhận thống nhất. |
| `templates/auth/orders.html` | Account tabs theo quyền, badge/empty state/xác nhận thống nhất. |
| `templates/auth/password.html` | Account tabs theo quyền, badge/empty state/xác nhận thống nhất. |
| `templates/auth/public_product.html` | Ảnh đơn theo dữ liệu thật, khối mua hàng/thông số và badge xác minh có text. |
| `templates/auth/reviews.html` | Account tabs theo quyền, badge/empty state/xác nhận thống nhất. |
| `templates/auth/users.html` | Badge trạng thái tài khoản, giữ nguyên scope quản lý và tất cả hành động. |
| `templates/auth/vouchers.html` | Voucher card có trạng thái, mã dạng vé, điều kiện và CTA từ dữ liệu hiện có. |
| `templates/base.html` | Header mua sắm, chuyển không gian quản trị, dropdown, skip link, footer và phân bố layout theo quyền. |
| `templates/components/admin_sidebar.html` | Macro icon/navigation/KPI/account tabs và sidebar chia nhóm theo permission; tái sử dụng Jinja. |
| `templates/components/ui.html` | Macro icon/navigation/KPI/account tabs và sidebar chia nhóm theo permission; tái sử dụng Jinja. |
| `templates/customers/detail.html` | Bọc bảng trong vùng cuộn ngang để bảo vệ layout mobile. |
| `templates/customers/form.html` | Label liên kết input, ký hiệu bắt buộc, section và giữ toàn bộ dữ liệu không bí mật khi validation lỗi. |
| `templates/customers/list.html` | Header, filter có label/reset và giữ lựa chọn, bảng và trạng thái nhất quán. |
| `templates/dashboard/index.html` | Mô tả nghiệp vụ, loading, aria-live; giữ DOM ID và URL script hiện hữu. |
| `templates/error.html` | Error state có hướng quay về theo landing hiện hữu và danh mục. |
| `templates/home.html` | KPI và thẻ truy cập nhanh theo permission. |
| `templates/orders/list.html` | Header, filter có label/reset và giữ lựa chọn, bảng và trạng thái nhất quán. |
| `templates/products/detail.html` | Bọc bảng trong vùng cuộn ngang để bảo vệ layout mobile. |
| `templates/products/form.html` | Label liên kết input, ký hiệu bắt buộc, section và giữ toàn bộ dữ liệu không bí mật khi validation lỗi. |
| `templates/products/list.html` | Label/bộ lọc nâng cao, giữ query khi phân trang và bỏ liên kết disabled khỏi tab order. |
| `templates/promotions/detail.html` | Bọc bảng trong vùng cuộn ngang để bảo vệ layout mobile. |
| `templates/promotions/form.html` | Label liên kết input, ký hiệu bắt buộc, section và giữ toàn bộ dữ liệu không bí mật khi validation lỗi. |
| `templates/promotions/list.html` | Header, filter có label/reset và giữ lựa chọn, bảng và trạng thái nhất quán. |
| `templates/reviews/list.html` | Header, filter có label/reset và giữ lựa chọn, bảng và trạng thái nhất quán. |
| `tests/test_shopping.py` | Chấp nhận aria-hidden="true" hợp lệ trong assertion; vẫn chặn supplierPassword và giá trị fixture bí mật. |
| `tests/test_ui_regression.py` | 15 test bổ sung: sidebar của 8 vai trò, query phân trang, 5 bộ lọc và giữ/escape form lỗi. |

Bằng chứng sinh trong lần chạy này: `docs/mint-lavender-test-results.xml`, `docs/shopping-replica-results.xml`, ảnh `docs/shopping-ui/`, ảnh và kết quả `docs/mint-lavender-ui/`. Ảnh dùng dữ liệu test tổng hợp, không phải dữ liệu khách hàng thật.

## C. Thiết kế mới

- Primary `#14B8A6`, hover `#0F9488`, nền `#CCFBF1`; secondary `#A78BFA`/`#EDE9FE`; accent `#FB7185`/`#FFE4E6`; nền trang `#F5F7FF`, surface trắng. Primary button dùng mint đậm `#087568` với chữ trắng để đạt AA. Lavender/pink dùng mực đậm trên nền sáng.
- Chữ chính `#243047`; chữ phụ điều chỉnh từ `#64748B` sang `#5F6F85` để đạt 4.79:1 trên nền trang. Viền input `#8593A7` đạt 3.12:1 trên trắng. Giữ nguyên tinh thần bảng màu yêu cầu.
- Font Inter nếu máy đã có, fallback Segoe UI/Arial hỗ trợ tiếng Việt; body 15px, title 24–30px. Radius 8/12/16/20px, spacing theo thang 4–48px.
- Shopping: hero gọn, product grid 1/2/3/4 cột theo viewport, ảnh contain, tồn kho/rating thật, voucher dạng vé, cart/checkout 2 cột desktop và 1 cột mobile, account tabs.
- Admin: sidebar desktop ở >=1200px; offcanvas mobile có focus trap/Escape. KPI, module card, bảng header mint, hover lavender và status có cả chữ/màu.
- Accessibility: skip link, label/input, required marker, focus-visible, bảng có vùng cuộn focus được, password toggle với aria-pressed, hỗ trợ reduced motion. Không thêm animation liên tục.

## D. Kiểm thử

Dùng `.venv\Scripts\python.exe` thay cho Python hệ thống. Kết quả cuối được lưu kèm XML/JSON.

| Lệnh / kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q --junitxml=docs/mint-lavender-test-results.xml` | PASS: 239 test, SKIP: 15 test cần MongoDB thật. |
| `python scripts/verify_shopping_replica.py` | PASS: 15/15 test tích hợp MongoDB thật; Edge desktop/mobile chạy trọn mua sắm. Script tạo replica container ngẫu nhiên riêng và tự dọn. |
| `python scripts/verify_mint_ui.py` | PASS: 85 mục kiểm tra ở 5 viewport; kết quả chi tiết: [results.json](mint-lavender-ui/results.json). |
| `python -m compileall -q app.py config.py db repositories routes services scripts` | PASS. |
| `node --check static/js/app.js` | PASS. |
| `node --check static/js/dashboard.js` | PASS. |
| `node --check static/js/reports.js` | PASS. |
| `docker compose config --quiet` | PASS; cùng bước xác thực cấu hình như `docker compose config`, không in credential đã nội suy. |
| `git diff --check` | PASS. |
| 11 cặp màu chữ/control | PASS; số đo cụ thể: [contrast.json](mint-lavender-ui/contrast.json). |

Luồng đã xác minh:

- Guest: catalog, tìm kiếm/lọc, chi tiết, đánh giá approved, login; danh mục rỗng có đường quay lại.
- Customer trên replica thật: đăng nhập, thêm giỏ, áp mã, tạo quote, bỏ/áp lại mã ở checkout mà giữ số điện thoại, đặt COD, xem đơn, đánh giá từ đơn đủ điều kiện, hủy pending. Suite HTTP kiểm tra thêm sửa số lượng/xóa, giá/điều kiện mã/ownership/CSRF và lỗi quote.
- Admin trên replica: xác nhận/hoàn tất đơn qua button name/value; các trang quản trị, thống kê, báo cáo và tài khoản trên Edge. CRUD và validation qua test tự động.
- 8 vai trò: route/method matrix hiện có, sidebar chỉ chứa đúng destination được phép; scope tài khoản và sở hữu đơn/review được kiểm tra.
- UI: 360/390/768/1024/1440px, không cuộn ngang toàn trang; menu mở/đóng, Escape, mật khẩu hiện/ẩn, skip link; dashboard loading kết thúc, lỗi một API giữ nhóm khác, trạng thái rỗng; reduced motion; không có JS exception ngoài lỗi API chủ động mô phỏng.
- Mô phỏng không gian hiển thị khi zoom 200% bằng CSS viewport 720px từ desktop 1440px. Chưa thao tác zoom thực trong giao diện browser hay kiểm thử screen reader thật.

Giới hạn môi trường: Mongomock phát cảnh báo `datetime.utcnow()` từ dependency. Một số lượt sandbox không ghi được cache pytest hoặc đọc Docker config; lượt cần Docker/network đã chạy trong môi trường được cấp quyền và có kết quả thực. Không đổi CSP, authentication hay CSRF để chạy browser. Bootstrap vẫn dùng CDN hiện hữu, cần kết nối mạng ở lần tải đầu.

## E. Bảo toàn bảo mật và nghiệp vụ

Không sửa `routes/`, `services/`, `repositories/`, `db/`, `app.py`, `config.py`, schema hay cấu hình Docker. Không đổi endpoint, HTTP method, API envelope, CRUD, RBAC, quyền sở hữu, phiên đăng nhập hoặc tính toán giá/tồn kho/mã/checkout/review.

Mọi form POST giữ CSRF. Fetch wrapper vẫn chỉ bổ sung X-CSRF-Token cho same-origin POST/PUT/PATCH/DELETE. Checkout giữ action/key, confirmation, formnovalidate/formaction của nút áp mã và name/value của submitter. Test replica bao gồm rollback, checkout đồng thời/replay, quote hết hạn/sai chủ/thay đổi giỏ và vòng đời tồn kho/lượt mã.

Không đưa dữ liệu API chưa escape vào HTML. Nội dung động dùng textContent hoặc escapeHtml; Jinja giữ autoescape. Không thêm đăng ký công khai, quên mật khẩu, gallery nhiều ảnh, giảm giá giả hay lộ lượt dùng mã nội bộ. Không import/reset hoặc chỉnh sửa dữ liệu thật, không commit/push.

## F. Kết quả và cách chạy

Đã triển khai giao diện thống nhất cho mua sắm, account, overview/dashboard, các trang quản trị và báo cáo. Các kiểm thử nghiệp vụ, phân quyền và giao dịch nêu trên đạt. Xem [catalog desktop](mint-lavender-ui/1440-guest-catalog.png), [dashboard desktop](mint-lavender-ui/1440-dashboard.png), [catalog mobile](mint-lavender-ui/360-guest-catalog.png), [dashboard mobile](mint-lavender-ui/360-dashboard.png), [checkout mobile trên replica](shopping-ui/mobile-checkout.png).

Chạy ứng dụng theo cấu hình `.env` hiện có:

```powershell
.\.venv\Scripts\python.exe app.py
```

Mở `/catalog` và `/login` tại host/cổng ứng dụng in ra; `.env.example`/README dùng `http://127.0.0.1:5002`. Nếu dùng Docker hiện hữu, build lại app bằng `docker compose up --build -d app`; không chạy thêm Python cùng cổng. Chưa tự restart/deploy bản ứng dụng đang phục vụ người dùng.

Chạy lại kiểm tra giao diện (cần Playwright và Microsoft Edge đã cài):

```powershell
.\.venv\Scripts\python.exe scripts/verify_mint_ui.py
.\.venv\Scripts\python.exe scripts/verify_shopping_replica.py
```

Phần chưa xác minh: Safari/Firefox, thiết bị vật lý, screen reader thực, zoom browser thực, chứng nhận WCAG toàn diện, performance/load/HA production. Số đo tương phản là 11 cặp màu chủ chốt, không phải audit mọi pixel/overlay. Không có thay đổi backend đang chờ hoàn tất.
