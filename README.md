# Quản lý chương trình khuyến mãi và đánh giá sản phẩm

Ứng dụng web sử dụng Flask, PyMongo và MongoDB để quản lý sản phẩm, chương trình khuyến mãi, khách hàng, đánh giá và đơn hàng.

Đã có **khu mua sắm CUSTOMER**: danh mục tìm/lọc/phân trang, giỏ lưu MongoDB, áp mã,
đặt COD bằng transaction, hủy pending, theo dõi đơn và đánh giá. Checkout cần replica set và đối soát lượt mã;
standalone vẫn xem danh mục/tra cứu được. [Cách chạy demo, chuyển dữ liệu an toàn và kết quả kiểm thử](docs/SHOPPING.md).
Dùng một stack: `docker compose up --build -d`, web **http://127.0.0.1:5002**, MongoDB **localhost:27018**.
Quản lý và mua sắm dùng chung database, tài khoản và dữ liệu.

Đăng nhập bằng mọi vai trò đều chuyển đến `/catalog` trước; các tab quản lý vẫn theo quyền.
50 sản phẩm demo có ảnh lưu trong `static/img/products/`, dùng chung cho danh mục và trang quản lý.

Ứng dụng đã có authentication và RBAC, gồm ADMIN và **Quản trị viên tài khoản (ACCOUNT_MANAGER)**.
Chi tiết phạm vi, bộ lọc, phân trang và API: [quản lý tài khoản](docs/ACCOUNT_MANAGEMENT.md).
**Đọc [hướng dẫn bảo mật và tạo ADMIN](docs/SECURITY.md)
trước khi chạy**: không có tài khoản mặc định; các trang/API nội bộ yêu cầu đăng nhập.
Danh mục công khai tại `/catalog`. Ma trận quyền: [RBAC_MATRIX.md](docs/RBAC_MATRIX.md);
route/method: [SECURITY_ROUTES.md](docs/SECURITY_ROUTES.md); bằng chứng test:
[SECURITY_TESTS.md](docs/SECURITY_TESTS.md). Cấu hình Docker/credential hiện hành trong hướng dẫn bảo mật
được ưu tiên so với các ví dụ cài đặt ban đầu bên dưới.

## Khởi động nhanh

Dùng duy nhất `docker-compose.yml` cho cả quản lý và mua sắm:

```bash
docker compose up --build -d
docker compose exec app python -m flask --app app:create_app reconcile-promotion-usage
```

Mở **http://127.0.0.1:5002**. `.env` cần SECRET_KEY và credential MongoDB
như `.env.example`. `FLASK_PORT=5002` là cổng web; `MONGO_DOCKER_PORT=27018`
là cổng MongoDB cho Compass. Chọn authSource đúng MONGO_DB và directConnection=true.
Sau khi import khuyến mãi/đơn hàng, chạy lại lệnh đối soát ở trên.
Tạo ADMIN khi database mới bằng `docker compose exec app python -m flask --app app:create_app bootstrap-admin`.
Dừng bằng `docker compose down`, giữ volume; không dùng `down -v`.

`.venv` dùng cho phát triển/kiểm thử: `source .venv/Scripts/activate`, `python -m pytest -q`.
Không chạy thêm `python app.py` khi Docker đã phục vụ web cổng 5002.
Nếu chọn chạy Python thay Docker: `docker compose stop app`, sau đó `python app.py`.
Trong `APP_ENV=development`, Python tự nạp lại khi sửa mã; debug console vẫn tắt.
Sau lần cập nhật cơ chế khởi chạy này, dừng tiến trình cũ bằng Ctrl+C và chạy lại một lần.
Chi tiết: [SHOPPING.md](docs/SHOPPING.md).

Chức năng chính:

- mô hình dữ liệu MongoDB dạng document;
- embedded document, array và reference logic;
- CRUD bằng PyMongo;
- truy vấn CB01–CB12;
- aggregation NC01–NC10;
- index và `explain()`;
- kết nối ứng dụng Flask với MongoDB;
- import/export và backup/restore.

## 1. Công nghệ sử dụng

- Python 3.11 trở lên;
- Flask 3;
- PyMongo;
- MongoDB;
- HTML5, CSS3, JavaScript thuần;
- Bootstrap 5;
- Docker và Docker Compose;
- Gunicorn khi chạy trong container;
- Pytest và Mongomock cho kiểm thử.

Frontend không sử dụng React, Vue, Angular, TypeScript hoặc Tailwind.

## 2. Yêu cầu trước khi cài đặt

Máy Windows cần có:

1. **Git**: dùng để clone source code.
2. **Python 3.11+**: nên chọn tùy chọn `Add Python to PATH` khi cài.
3. **MongoDB Community Server**: MongoDB phải chạy tại `127.0.0.1:27017` hoặc một URI khác do người dùng cấu hình.
4. **Navicat for MongoDB** hoặc **mongosh**: không bắt buộc để chạy ứng dụng, chỉ dùng để quản trị và kiểm tra MongoDB.

Nếu chọn chạy bằng Docker, chỉ cần **Git** và **Docker Desktop**; Python và MongoDB trên máy host chỉ cần thiết khi chạy local hoặc khi muốn container ứng dụng dùng database hiện có trên máy.

Nếu máy đã có database `QL_KHUYENMAI_DANHGIA` như ảnh minh họa thì **không cần file `DB.js` và không chạy lại script này**. `DB.js` chỉ là script khởi tạo dữ liệu cho một MongoDB trống.

Kiểm tra Git và Python:

```powershell
git --version
py --version
```

Nếu lệnh `py` không tồn tại, thử:

```powershell
python --version
```

Kiểm tra mongosh nếu sử dụng dòng lệnh:

```powershell
mongosh --version
```

## 3. Clone dự án

Mở PowerShell tại thư mục muốn lưu source:

```powershell
cd D:\StudyMaterials\HK7\NoSQL\Project
git clone <URL_GIT_CUA_DU_AN> product_promotion_review_management
cd product_promotion_review_management
```

Thay `<URL_GIT_CUA_DU_AN>` bằng URL GitHub/GitLab thực tế.

Nếu đã nhận source dưới dạng ZIP:

1. Giải nén source.
2. Mở PowerShell trong thư mục chứa `app.py`.
3. Kiểm tra vị trí hiện tại:

```powershell
Get-Location
Test-Path .\app.py
Test-Path .\requirements.txt
```

Hai lệnh `Test-Path` phải trả về `True`.

## 4. Cách ứng dụng kết nối dữ liệu

Navicat không lưu database trong một file riêng. Navicat là công cụ quản trị; dữ liệu thực tế nằm trong tiến trình **MongoDB Server**. Ứng dụng Flask dùng PyMongo để kết nối trực tiếp tới cùng server và database mà Navicat đang mở:

```text
Navicat ────────┐
                ├── MongoDB Server: 127.0.0.1:27017
Flask + PyMongo ┘                    └── QL_KHUYENMAI_DANHGIA
```

Khi ứng dụng chạy, luồng dữ liệu là:

```text
Trình duyệt → Flask → PyMongo → MongoDB Server
```

Ứng dụng **không đọc `DB.js` khi chạy**, không dùng dữ liệu giả từ file và không tự động xóa/nạp lại database. Mọi thao tác CRUD, thống kê và biểu đồ đều lấy trực tiếp từ 5 collection trong MongoDB.

## 5–12. Cài đặt và chạy

Theo mục **Khởi động nhanh** ở đầu tài liệu. Dùng một `docker-compose.yml`,
web cổng 5002 và MongoDB cổng 27018, chung database cho quản lý và mua sắm.
Không cần chạy thêm MongoDB local hoặc `python app.py` để sử dụng website.
Các bước nhập dữ liệu, bootstrap ADMIN, backup và đối soát xem [SHOPPING.md](docs/SHOPPING.md).
Không nạp lại `DB.js` vào database đang dùng vì script khởi tạo có thể xóa dữ liệu.

## 13. Chạy kiểm thử

Bộ test sử dụng Mongomock và database test độc lập, không xóa dữ liệu thật.

Cài dependency dành cho phát triển và kiểm thử:

```powershell
python -m pip install -r requirements-dev.txt
```

```powershell
python -m pytest -q
```

Kết quả hiện tại:

```text
Xem kết quả đầy đủ trong docs/SECURITY_TESTS.md (gồm MongoDB thật và Docker).
```

Kiểm tra cú pháp toàn bộ source Python:

```powershell
python -m compileall -q app.py config.py db repositories routes services scripts
```

Kiểm tra cú pháp JavaScript dashboard nếu máy có Node.js:

```powershell
node --check static\js\dashboard.js
```

## 14. Cấu trúc dự án

```text
product_promotion_review_management/
├── app.py
├── config.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── README.md
├── db/
│   ├── mongo.py
│   └── indexes.py
├── repositories/
│   ├── product_repository.py
│   ├── promotion_repository.py
│   ├── customer_repository.py
│   ├── review_repository.py
│   ├── order_repository.py
│   └── report_repository.py
├── services/
│   ├── product_service.py
│   ├── promotion_service.py
│   ├── customer_service.py
│   ├── review_service.py
│   ├── order_service.py
│   └── dashboard_service.py
├── routes/
│   ├── web_routes.py
│   └── api_routes.py
├── templates/
├── static/
│   ├── css/app.css
│   ├── img/logo.svg
│   └── js/
├── scripts/
├── tests/
└── docs/
    └── SCHEMA.md
```

Luồng xử lý chính:

```text
Browser → Flask route → Service → Repository → PyMongo → MongoDB
```

## 15. API

Các nhóm API chính:

- `/api/products`
- `/api/promotions`
- `/api/customers`
- `/api/reviews`
- `/api/orders`
- `/api/dashboard/summary`
- `/api/dashboard/ratings`
- `/api/dashboard/promotions`
- `/api/dashboard/sales`

Response JSON có cấu trúc:

```json
{
  "success": true,
  "message": "Thành công",
  "data": {}
}
```

## 16. Import, export và backup

Xuất collection ra JSON:

```powershell
New-Item -ItemType Directory -Force .\exports
mongoexport --uri="mongodb://127.0.0.1:27017" --db="QL_KHUYENMAI_DANHGIA" --collection="customers" --jsonArray --out=".\exports\customers.json"
```

Sao lưu toàn bộ database:

```powershell
mongodump --uri="mongodb://127.0.0.1:27017" --db="QL_KHUYENMAI_DANHGIA" --out=".\backup"
```

Khôi phục vào database kiểm tra riêng:

```powershell
mongorestore --uri="mongodb://127.0.0.1:27017" --nsFrom="QL_KHUYENMAI_DANHGIA.*" --nsTo="QL_KHUYENMAI_DANHGIA_RESTORE.*" ".\backup"
```

## 17. Xử lý lỗi thường gặp

### Docker CLI có nhưng Docker Engine chưa chạy

Thông báo thường gặp:

```text
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified
```

Mở Docker Desktop, chờ đến khi trạng thái Engine là **Running**, rồi kiểm tra:

```powershell
docker version
docker compose version
docker compose config
```

Sau đó chạy lại lệnh `docker compose up --build -d` phù hợp ở mục 12.

### Không kết nối được MongoDB

Thông báo thường gặp:

```text
Không thể kết nối MongoDB
```

Kiểm tra:

```powershell
Get-Service MongoDB
python scripts\check_connection.py
```

Kiểm tra `MONGO_URI` trong `.env`. Nếu MongoDB chạy cổng khác, sửa lại URI.

### Database không có dữ liệu

Chạy:

```powershell
python scripts\verify_database.py
```

Nếu database trống, import JSON demo vào đúng MongoDB cổng 27018 theo data/demo/README.md.

### Chữ tiếng Việt bị biến thành dấu hỏi

Kiểm tra encoding UTF-8 khi nhập JSON. Giữ nguyên dữ liệu gốc và bản backup trước khi sửa.
Nếu đã có bản backup đúng, khôi phục lại database theo mục 16 thay vì sửa chuỗi lỗi thủ công.

### Cổng 5002 đã được sử dụng

Kiểm tra PID:

```powershell
netstat -ano | findstr :5002
```

Kiểm tra tiến trình trước khi dừng:

```powershell
Get-Process -Id <PID>
```

Chỉ khi đã xác nhận đó là Flask cũ của dự án, dừng bằng:

```powershell
Stop-Process -Id <PID>
```

Hoặc đổi cổng trong `.env`:

```dotenv
FLASK_PORT=5002
```

Sau đó mở `http://127.0.0.1:5002`.

### Giao diện cũ hoặc dashboard báo lỗi sau khi cập nhật code

1. Dừng tất cả terminal đang chạy `python app.py`.
2. Chỉ khởi động một instance:

```powershell
docker compose up --build -d
```

3. Mở đúng cổng được in trong terminal.
4. Nhấn `Ctrl + F5` hoặc `Ctrl + Shift + R`.
5. Kiểm tra API trực tiếp:

```text
http://127.0.0.1:5002/api/dashboard/summary
http://127.0.0.1:5002/api/dashboard/ratings
http://127.0.0.1:5002/api/dashboard/promotions
http://127.0.0.1:5002/api/dashboard/sales
```

Các API phải trả `"success": true`.

### PowerShell không kích hoạt được virtual environment

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### ModuleNotFoundError

Đảm bảo đang dùng Python trong `.venv`:

```powershell
Get-Command python
python -m pip install -r requirements.txt
```

Đường dẫn Python phải trỏ tới `.venv\Scripts\python.exe`.

## 18. Phạm vi không triển khai

Dự án không triển khai:

- thanh toán trực tuyến;
- vận chuyển;
- giỏ hàng phức tạp;
- OAuth;
- phân cấp role ngầm định (quyền được cấp tường minh qua RBAC);
- microservice;
- Kubernetes;
- cloud production.

Chi tiết cấu trúc collection nằm trong [mô hình dữ liệu](docs/SCHEMA.md). Navicat for MongoDB là công cụ quản trị; ứng dụng Flask thực hiện CRUD, báo cáo và aggregation trực tiếp trên MongoDB.
