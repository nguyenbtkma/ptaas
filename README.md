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

## Cài đặt & Chạy

### Bước 1: Clone & Setup
```bash
cd ptaas
cp .env.example .env
```

### Bước 2: Cấu hình .env
```bash
# Sửa DEFECTDOJO_API_KEY sau khi khởi tạo
vim .env
```

### Bước 3: Khởi động Services
```bash
docker-compose up -d
```

### Bước 4: Lấy DefectDojo API Key
```bash
# Truy cập DefectDojo
open http://localhost:8080

# Login: admin / Admin@123
# Vào: Configuration → API v2 Key → Create Key
# Copy key vào .env
```

### Bước 5: Restart Backend
```bash
docker-compose restart backend celery
```

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
