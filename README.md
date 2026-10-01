# Quản lý chương trình khuyến mãi và đánh giá sản phẩm

Ứng dụng web sử dụng Flask, PyMongo và MongoDB để quản lý sản phẩm, chương trình khuyến mãi, khách hàng, đánh giá và đơn hàng.

## Khởi động nhanh

Sau khi clone dự án, chọn một trong các cách sau.

### Chạy local với MongoDB tại `localhost:27017`

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python scripts\check_connection.py
python app.py
```

Mở `http://127.0.0.1:5001`.

### Chạy ứng dụng trong Docker, dùng MongoDB hiện có trên máy

Phù hợp khi Navicat đang dùng database tại `localhost:27017`:

```powershell
docker compose -f docker-compose.host-mongodb.yml up --build -d
docker compose -f docker-compose.host-mongodb.yml logs -f app
```

Dừng ứng dụng:

```powershell
docker compose -f docker-compose.host-mongodb.yml down
```

### Chạy cả ứng dụng và MongoDB trong Docker

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f app
```

Ứng dụng chạy tại `http://127.0.0.1:5001`; MongoDB Docker được xuất tại `localhost:27018` và lưu dữ liệu trong Docker volume. Dừng stack nhưng giữ dữ liệu bằng:

```powershell
docker compose down
```

Docker Desktop phải được mở và Docker Engine phải ở trạng thái **Running** trước khi chạy các lệnh Docker. Hướng dẫn cấu hình, chuyển dữ liệu và xử lý lỗi chi tiết nằm tại mục 11–12 và mục 17.

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

## 5. Khởi động MongoDB

### Cách 1: MongoDB chạy dưới dạng Windows Service

Kiểm tra dịch vụ:

```powershell
Get-Service MongoDB
```

Nếu trạng thái là `Stopped`, mở PowerShell bằng quyền Administrator và chạy:

```powershell
Start-Service MongoDB
```

### Cách 2: MongoDB được quản lý bởi công cụ khác

Nếu dùng MongoDB Compass, Laragon hoặc một bộ cài riêng, hãy khởi động MongoDB từ công cụ tương ứng và đảm bảo server lắng nghe tại:

```text
mongodb://127.0.0.1:27017
```

Kiểm tra trực tiếp bằng mongosh:

```powershell
mongosh "mongodb://127.0.0.1:27017" --eval "db.adminCommand({ ping: 1 })"
```

Kết quả thành công phải chứa `ok: 1`.

## 6. Tạo virtual environment

Tại thư mục chứa `app.py`, chạy:

```powershell
py -m venv .venv
```

Kích hoạt môi trường ảo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Nếu PowerShell báo không cho phép chạy script, chỉ thay đổi policy cho cửa sổ hiện tại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Sau khi kích hoạt, đầu dòng lệnh sẽ có tiền tố `(.venv)`.

Nếu sử dụng Windows CMD:

```bat
.venv\Scripts\activate.bat
```

## 7. Cài dependency

Nâng cấp pip và cài thư viện:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Kiểm tra Flask và PyMongo:

```powershell
python -c "import flask, pymongo; print('Flask:', flask.__version__); print('PyMongo:', pymongo.version)"
```

Nếu không có lỗi import thì dependency đã được cài thành công.

## 8. Tạo file cấu hình .env

Sao chép file mẫu:

```powershell
Copy-Item .env.example .env
```

Mở `.env` và kiểm tra nội dung:

```dotenv
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB=QL_KHUYENMAI_DANHGIA
FLASK_HOST=127.0.0.1
FLASK_PORT=5001
SECRET_KEY=thay-bang-chuoi-ngau-nhien
```

Có thể tạo `SECRET_KEY` ngẫu nhiên bằng Python:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Sao chép kết quả và thay giá trị `SECRET_KEY` trong `.env`.

Không commit file `.env` lên Git.

## 9. Chọn database hiện có hoặc khởi tạo database mới

Database bắt buộc:

```text
QL_KHUYENMAI_DANHGIA
```

### Trường hợp A: Máy đã có database trong Navicat (khuyến nghị)

Nếu Navicat đã hiển thị database `QL_KHUYENMAI_DANHGIA` gồm `products`, `promotions`, `customers`, `reviews` và `orders`, hãy giữ nguyên dữ liệu và **bỏ qua toàn bộ phần chạy `DB.js` bên dưới**.

Ứng dụng sẽ kết nối tới database này bằng hai biến trong `.env`:

```dotenv
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB=QL_KHUYENMAI_DANHGIA
```

Chuyển thẳng tới mục 10 để kiểm tra kết nối.

### Trường hợp B: MongoDB mới, chưa có database

Chỉ dùng `DB.js` để tạo dữ liệu ban đầu khi server MongoDB chưa có database hoặc các collection đang trống. Sau khi nạp dữ liệu chuẩn, database có tối thiểu:

| Collection | Số document |
|---|---:|
| products | 12 |
| promotions | 6 |
| customers | 10 |
| reviews | 14 |
| orders | 12 |

> Cảnh báo: `DB.js` có lệnh xóa dữ liệu cũ trong đúng 5 collection trước khi chèn lại. Không chạy file này trên database đang có dữ liệu cần giữ.

### Cách 1: Chạy bằng Navicat for MongoDB

1. Mở Navicat for MongoDB.
2. Tạo hoặc mở kết nối tới `mongodb://127.0.0.1:27017`.
3. Chọn **New Query**.
4. Mở file `DB.js` với encoding UTF-8.
5. Nếu Navicat báo lỗi tại dòng `show collections;`, comment dòng đó thành:

```javascript
// show collections;
```

6. Chạy toàn bộ script.
7. Refresh kết nối và kiểm tra database `QL_KHUYENMAI_DANHGIA`.

### Cách 2: Chạy bằng mongosh trong PowerShell

File nguồn có meta-command `show collections;` nằm trong IIFE. Lệnh sau chỉ loại dòng này trên luồng chạy, không sửa file gốc. Việc cấu hình UTF-8 là bắt buộc để không làm tên tiếng Việt thành dấu `?`.

```powershell
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$dbScript = Get-Content -LiteralPath "..\DB.js" -Raw -Encoding UTF8
$compatibleScript = $dbScript -replace '(?m)^show collections;\r?\n', ''
$compatibleScript | mongosh "mongodb://127.0.0.1:27017/QL_KHUYENMAI_DANHGIA"
```

Nếu `DB.js` nằm ở vị trí khác, thay `..\DB.js` bằng đường dẫn đầy đủ tới file trên máy.

## 10. Kiểm tra MongoDB trước khi chạy Flask

Đảm bảo virtual environment đang được kích hoạt, sau đó chạy:

```powershell
python scripts\check_connection.py
```

Kết quả mong đợi:

```text
Kết nối MongoDB thành công: QL_KHUYENMAI_DANHGIA
```

Kiểm tra số lượng document:

```powershell
python scripts\verify_database.py
```

Kiểm tra index:

```powershell
python scripts\check_indexes.py
```

Kết quả mong đợi:

```text
Kết quả: ĐỦ INDEX
```

Kiểm tra execution plan của truy vấn review:

```powershell
python scripts\explain_review_query.py
```

Kết quả phải hiển thị `winningPlan`, `totalDocsExamined`, `totalKeysExamined` và `executionTimeMillis`.

## 11. Chạy local

Trước khi chạy, kiểm tra cổng 5001:

```powershell
netstat -ano | findstr :5001
```

Nếu không có dòng `LISTENING`, chạy ứng dụng:

```powershell
python app.py
```

Kết quả mong đợi:

```text
* Running on http://127.0.0.1:5001
```

Mở trình duyệt tại:

```text
http://127.0.0.1:5001
```

Các trang chính:

| Chức năng | URL |
|---|---|
| Tổng quan | `http://127.0.0.1:5001/` |
| Sản phẩm | `http://127.0.0.1:5001/san-pham` |
| Khuyến mãi | `http://127.0.0.1:5001/khuyen-mai` |
| Khách hàng | `http://127.0.0.1:5001/khach-hang` |
| Đánh giá | `http://127.0.0.1:5001/danh-gia` |
| Đơn hàng | `http://127.0.0.1:5001/don-hang` |
| Dashboard | `http://127.0.0.1:5001/thong-ke` |
| Báo cáo nghiệp vụ | `http://127.0.0.1:5001/bao-cao` |

Để dừng ứng dụng, quay lại terminal và nhấn:

```text
Ctrl + C
```

Không chạy nhiều cửa sổ `python app.py` cùng lúc.

## 12. Chạy bằng Docker

Dự án cung cấp ba file:

- `Dockerfile`: đóng gói ứng dụng Flask và chạy bằng Gunicorn;
- `docker-compose.host-mongodb.yml`: chạy ứng dụng trong Docker nhưng dùng MongoDB hiện có trên máy tại `localhost:27017`;
- `docker-compose.yml`: chạy cả ứng dụng và một MongoDB riêng trong Docker.

### Cách A: Container ứng dụng dùng MongoDB hiện có trên máy

Đây là lựa chọn phù hợp khi Navicat đang kết nối `localhost:27017` và database `QL_KHUYENMAI_DANHGIA` đã có dữ liệu.

Trước tiên, dừng ứng dụng local nếu đang chiếm cổng `5001`. Sau đó chạy tại thư mục dự án:

```powershell
docker compose -f docker-compose.host-mongodb.yml up --build -d
```

Kiểm tra container và log:

```powershell
docker compose -f docker-compose.host-mongodb.yml ps
docker compose -f docker-compose.host-mongodb.yml logs -f app
```

Khi log cho biết Gunicorn đang lắng nghe tại `0.0.0.0:5001`, mở:

```text
http://127.0.0.1:5001
```

Container kết nối tới MongoDB host bằng URI nội bộ:

```text
mongodb://host.docker.internal:27017
```

Navicat vẫn tiếp tục dùng `localhost:27017`; cả Navicat và ứng dụng container cùng đọc một database trên máy.

Dừng container:

```powershell
docker compose -f docker-compose.host-mongodb.yml down
```

Nếu container báo không kết nối được MongoDB, kiểm tra MongoDB Windows Service đang chạy và tường lửa cho phép Docker Desktop kết nối tới cổng `27017`.

### Cách B: Chạy cả Flask và MongoDB trong Docker

Chạy toàn bộ stack:

```powershell
docker compose up --build -d
```

Kiểm tra trạng thái và xem log:

```powershell
docker compose ps
docker compose logs -f app
```

Các địa chỉ sau được sử dụng:

| Thành phần | Địa chỉ trên máy host |
|---|---|
| Ứng dụng | `http://127.0.0.1:5001` |
| MongoDB Docker | `mongodb://127.0.0.1:27018` |

MongoDB Docker dùng cổng `27018` để không xung đột với MongoDB local tại `27017`. Trong Navicat, tạo thêm kết nối `localhost:27018` nếu muốn quản trị database trong container.

MongoDB container là database độc lập và ban đầu chưa có dữ liệu. Ứng dụng không tự chạy `DB.js`, không tự seed và không xóa dữ liệu. Có thể sao chép database local sang Docker bằng:

```powershell
mongodump --uri="mongodb://127.0.0.1:27017" --db="QL_KHUYENMAI_DANHGIA" --out=".\backup"
mongorestore --uri="mongodb://127.0.0.1:27018" --drop --db="QL_KHUYENMAI_DANHGIA" ".\backup\QL_KHUYENMAI_DANHGIA"
```

Lệnh `--drop` chỉ xóa các collection tương ứng trong MongoDB Docker tại cổng `27018`; không tác động MongoDB local tại `27017`.

Dừng stack nhưng giữ dữ liệu MongoDB:

```powershell
docker compose down
```

Khởi động lại với dữ liệu đã lưu:

```powershell
docker compose up -d
```

Chỉ khi chắc chắn muốn xóa cả volume và toàn bộ dữ liệu MongoDB Docker mới chạy:

```powershell
docker compose down -v
```

### Build và chạy riêng Dockerfile

Build image:

```powershell
docker build -t ql-khuyen-mai:local .
```

Chạy image và kết nối MongoDB trên máy host:

```powershell
docker run --rm --name ql-khuyen-mai -p 127.0.0.1:5001:5001 -e MONGO_URI=mongodb://host.docker.internal:27017 -e MONGO_DB=QL_KHUYENMAI_DANHGIA -e SECRET_KEY=thay-bang-chuoi-ngau-nhien ql-khuyen-mai:local
```

Nhấn `Ctrl + C` để dừng container chạy trực tiếp.

### Đổi cổng Docker

Nếu cổng `5001` hoặc `27018` đang được sử dụng, đặt biến trước khi chạy Compose đầy đủ:

```powershell
$env:FLASK_PORT = "5002"
$env:MONGO_DOCKER_PORT = "27019"
docker compose up --build -d
```

Khi đó ứng dụng ở `http://127.0.0.1:5002` và MongoDB Docker ở `localhost:27019`.

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
25 passed
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
├── docker-compose.host-mongodb.yml
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

Nếu 5 collection đều bằng 0, chạy lại `DB.js` theo mục 9.

### Chữ tiếng Việt bị biến thành dấu hỏi

Nguyên nhân thường là nạp `DB.js` qua pipeline không sử dụng UTF-8. Nên xóa/nạp lại database bằng lệnh UTF-8 tại mục 9.
Nếu đã có bản backup đúng, khôi phục lại database theo mục 16 thay vì sửa chuỗi lỗi thủ công.

### Cổng 5001 đã được sử dụng

Kiểm tra PID:

```powershell
netstat -ano | findstr :5001
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
python app.py
```

3. Mở đúng cổng được in trong terminal.
4. Nhấn `Ctrl + F5` hoặc `Ctrl + Shift + R`.
5. Kiểm tra API trực tiếp:

```text
http://127.0.0.1:5001/api/dashboard/summary
http://127.0.0.1:5001/api/dashboard/ratings
http://127.0.0.1:5001/api/dashboard/promotions
http://127.0.0.1:5001/api/dashboard/sales
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
- phân quyền nhiều cấp;
- microservice;
- Kubernetes;
- cloud production.

Chi tiết cấu trúc collection nằm trong [mô hình dữ liệu](docs/SCHEMA.md). Navicat for MongoDB là công cụ quản trị; ứng dụng Flask thực hiện CRUD, báo cáo và aggregation trực tiếp trên MongoDB.
