# PTaaS - Penetration Testing as a Service

Nền tảng PTaaS hoàn chỉnh với API Gateway, Task Queue, và tích hợp các scanner bảo mật.

## Kiến trúc Hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                      PTaaS Platform                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │   FastAPI    │◄────►│    Celery    │                   │
│  │  (Gateway)   │      │   (Worker)   │                   │
│  └──────────────┘      └──────────────┘                   │
│         │                      │                           │
│         │                      ▼                           │
│         │              ┌──────────────┐                   │
│         │              │    Redis     │                   │
│         │              │   (Broker)   │                   │
│         │              └──────────────┘                   │
│         │                                                  │
│         ▼                                                  │
│  ┌──────────────────────────────────────┐                │
│  │        Security Scanners             │                │
│  │  ┌─────┐  ┌─────┐  ┌────────┐       │                │
│  │  │ Nmap│  │ ZAP │  │ SQLMap │       │                │
│  │  └─────┘  └─────┘  └────────┘       │                │
│  └──────────────────────────────────────┘                │
│         │                                                  │
│         ▼                                                  │
│  ┌──────────────┐      ┌──────────────┐                  │
│  │    MinIO     │      │  DefectDojo  │                  │
│  │  (Storage)   │      │  (Analysis)  │                  │
│  └──────────────┘      └──────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## Tính năng Chính

### 1. API Gateway (FastAPI)
- **POST /scan/nmap** - Quét network với Nmap
- **POST /scan/zap** - Quét web app với OWASP ZAP
- **POST /scan/sqlmap** - Quét SQL injection
- **GET /scan/status/{task_id}** - Theo dõi tiến độ quét
- **GET /results** - Lấy kết quả từ DefectDojo

### 2. Task Queue (Celery)
- Xử lý bất đồng bộ các tác vụ quét
- Theo dõi tiến độ real-time (0% → 100%)
- Retry mechanism khi có lỗi
- Concurrent execution

### 3. Zero-Disk Architecture
```
Scanner → Backend → MinIO (S3) → DefectDojo
         ↓
    [No Local Storage]
```

### 4. Cloud-Ready Configuration
- **Local**: MinIO, Docker, Redis
- **AWS**: S3, ECS, ElastiCache
- **Chỉ cần đổi .env - code không đổi**

## Yêu cầu Hệ thống

- **Docker**: v20.10+ và Docker Compose v2.0+
- **Python**: 3.11+ (nếu chạy locally mà không dùng Docker)
- **Git**: để clone repo
- **RAM**: ≥4GB (khuyến nghị ≥8GB)
- **Disk**: ≥10GB cho images, containers, và dữ liệu

## Cài đặt & Cấu hình

### Bước 1: Clone Repository
```bash
git clone https://github.com/nguyenbtkma/ptaas.git
cd ptaas
```

### Bước 2: Tạo file .env từ template
```bash
cp .env.example .env
```

### Bước 3: Cấu hình Biến Môi Trường (.env)

Mở file `.env` và điền các giá trị sau:

#### Database (PostgreSQL)
```env
DB_HOST=postgres
DB_PORT=5432
DB_NAME=defectdojo_db
DB_USER=postgres
DB_PASSWORD=postgres
```

#### Redis (Task Broker)
```env
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

#### MinIO (S3-Compatible Storage)
```env
S3_ENDPOINT=http://minio:9000
S3_BUCKET=ptaas
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
```

#### DefectDojo
```env
DEFECTDOJO_URL=http://nginx:8080
DEFECTDOJO_API_KEY=your-api-key-here  # Điền sau bước khởi tạo
```

#### ZAP Scanner
```env
ZAP_URL=http://zap:8080
ZAP_API_KEY=changeme
```

#### Backend Service
```env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DEBUG=False
```

**Lưu ý:** Các giá trị local (minio, redis, nginx) chỉ dùng trong Docker Compose. Nếu deploy AWS, thay bằng endpoint thực tế (RDS, ElastiCache, S3, v.v.).

### Bước 4: Khởi động Services
```bash
docker compose up -d
```

Kiểm tra tất cả container chạy:
```bash
docker compose ps
```

Chờ 30-60s để services khởi động hoàn toàn, đặc biệt DefectDojo DB.

### Bước 5: Lấy DefectDojo API Key

1. Truy cập DefectDojo: http://localhost:8080
2. Đăng nhập: **Username**: `admin` | **Password**: `Admin@123`
3. Vào **Configuration** → **API v2 Key**
4. Click **Create Key** (nếu chưa có)
5. **Copy API Key** từ danh sách

### Bước 6: Cập nhật .env với API Key
```bash
# Mở .env và sửa:
DEFECTDOJO_API_KEY=<your-copied-api-key>
```

### Bước 7: Restart Backend & Celery
```bash
docker compose restart backend celery
```

Verify logs:
```bash
docker compose logs -f backend celery
```

Nếu thấy `Task is ready` hoặc `Server running` → Thành công!

## Xác minh Cài đặt

Chạy test script để kiểm tra toàn bộ hệ thống:
```bash
chmod +x test_system.sh
./test_system.sh
```

Expected output:
- Health check: OK
- Nmap scan: Started
- ZAP scan: Started  
- Findings retrieved: N items

## Các Port & URL

| Service | Local URL | Credentials |
|---------|-----------|-------------|
| **FastAPI** | http://localhost:8000 | - |
| **FastAPI Docs** | http://localhost:8000/docs | - |
| **DefectDojo** | http://localhost:8080 | admin / Admin@123 |
| **MinIO** | http://localhost:9001 | minioadmin / minioadmin |
| **ZAP Proxy** | http://localhost:8090 | - |
| **Redis** | localhost:6379 | - |
| **PostgreSQL** | localhost:5432 | postgres / postgres |

## Troubleshooting

### Container không khởi động
```bash
docker compose logs <service-name>
# Ví dụ:
docker compose logs backend
docker compose logs defectdojo_uwsgi
```

### Celery worker không sẵn sàng
```bash
# Flush Redis để xóa old messages:
docker compose exec redis redis-cli FLUSHALL

# Restart Celery:
docker compose restart celery
```

### DefectDojo 403 API Key Invalid
- Kiểm tra `DEFECTDOJO_API_KEY` trong `.env` có đúng không
- Kiểm tra key đã tạo và chưa bị revoke
- Restart container: `docker compose restart backend celery`

### Kết nối MinIO thất bại
- Kiểm tra `S3_ENDPOINT=http://minio:9000` (không phải http://localhost)
- Kiểm tra `S3_ACCESS_KEY` và `S3_SECRET_KEY` khớp với DefectDojo container
- Xem logs MinIO: `docker compose logs minio`

## Sử dụng API

### Quét với Nmap
```bash
curl -X POST http://localhost:8000/scan/nmap \
  -H "Content-Type: application/json" \
  -d '{
    "target": "scanme.nmap.org",
    "options": "-sV -sC"
  }'

# Response:
{
  "task_id": "abc-123-xyz",
  "scan_type": "nmap",
  "target": "scanme.nmap.org",
  "status": "queued"
}
```

### Quét với ZAP
```bash
curl -X POST http://localhost:8000/scan/zap \
  -H "Content-Type: application/json" \
  -d '{
    "target": "http://testphp.vulnweb.com",
    "options": "active"
  }'
```

### Theo dõi Tiến độ
```bash
curl http://localhost:8000/scan/status/abc-123-xyz

# Response:
{
  "task_id": "abc-123-xyz",
  "state": "STARTED",
  "progress": 65,
  "status": "Active Scan: 65%"
}
```

### Lấy Kết quả
```bash
curl http://localhost:8000/results?limit=10
```

## Luồng Hoạt động Chi tiết

### Nmap Scan Flow
```
1. User gửi POST /scan/nmap
2. Backend tạo Celery task
3. Worker nhận task từ Redis
4. Execute: nmap -oX - target
5. Upload XML → MinIO
6. Import → DefectDojo
7. Return task result
```

### ZAP Scan Flow
```
1. User gửi POST /scan/zap
2. Backend tạo Celery task
3. Worker kết nối ZAP API
4. Spider website (0% → 100%)
5. Active Scan (0% → 100%)
6. Export JSON report
7. Upload → MinIO
8. Import → DefectDojo
```

## Cấu trúc Dự án

```
ptaas/
├── docker-compose.yml          # Orchestration
├── .env                        # Environment config
├── .env.example               # Template
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py            # FastAPI app
│       ├── models.py          # Pydantic models
│       ├── celery_app.py      # Celery config
│       ├── tasks.py           # Scan tasks
│       └── integrations/
│           ├── storage.py     # MinIO/S3 client
│           └── defectdojo.py  # DefectDojo client
│
└── scanners/
    ├── zap/
    ├── nmap/
    └── sqlmap/
```

## Chuyển sang AWS

### Local → AWS Mapping

| Component | Local | AWS |
|-----------|-------|-----|
| Database | postgres (container) | RDS PostgreSQL |
| Storage | MinIO | S3 |
| Cache | Redis (container) | ElastiCache |
| Backend | Docker Compose | ECS Fargate |
| Network | Docker bridge | VPC |

### Chỉ cần đổi .env:

**Local:**
```env
DB_HOST=postgres
S3_ENDPOINT=http://minio:9000
CELERY_BROKER_URL=redis://redis:6379/0
```

**AWS:**
```env
DB_HOST=ptaas.xyz.rds.amazonaws.com
S3_ENDPOINT=https://s3.amazonaws.com
CELERY_BROKER_URL=redis://elasticache.xyz.com:6379
```

**→ Code không đổi 1 dòng!**

## Monitoring & Logs

```bash
# Xem logs Backend
docker logs -f ptaas-backend

# Xem logs Celery Worker
docker logs -f ptaas-celery

# Xem logs ZAP
docker logs -f ptaas-zap

# Flower (Celery monitoring) - tùy chọn
docker run -p 5555:5555 \
  -e CELERY_BROKER_URL=redis://redis:6379/0 \
  mher/flower
```

## Security Notes

1. **API Key**: Đổi DEFECTDOJO_API_KEY trong production
2. **ZAP API Key**: Đổi ZAP_API_KEY (mặc định: changeme)
3. **MinIO**: Đổi MINIO_ROOT_USER/PASSWORD
4. **Secret Key**: Đổi SECRET_KEY trong .env

## Bước Tiếp theo

- [ ] Thêm authentication (JWT)
- [ ] Rate limiting
- [ ] Report generation (PDF)
- [ ] Email notifications
- [ ] Web Dashboard (React/Vue)
- [ ] Kubernetes deployment
- [ ] CI/CD pipeline

## License

MIT

## Contributing

Pull requests are welcome!

---

**Được xây dựng bởi PTaaS Team**
