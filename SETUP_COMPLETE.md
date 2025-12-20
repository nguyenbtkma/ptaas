# 🚀 Hướng dẫn Hoàn tất Setup PTaaS

## ✅ Trạng thái hiện tại

Tất cả services đã chạy thành công:
- ✅ Backend API (FastAPI) - http://localhost:8000
- ✅ Celery Worker - Đang chạy và nhận tasks  
- ✅ MinIO Storage - http://localhost:9001
- ✅ DefectDojo - http://localhost:8080
- ✅ ZAP Scanner - Ready
- ✅ Nmap Scanner - Ready
- ✅ SQLMap Scanner - Ready

## 🔑 Bước cuối: Lấy DefectDojo API Key

### 1. Truy cập DefectDojo
```bash
# Mở browser
http://localhost:8080
```

### 2. Đăng nhập
- **Username**: `admin`
- **Password**: `Admin@123`

### 3. Tạo API Key
1. Click vào **avatar** (góc trên bên phải)
2. Chọn **"API v2 Key (Token)"**
3. Click **"New Key"** hoặc copy key có sẵn
4. Copy API Key

### 4. Cập nhật .env
```bash
cd ~/ptaas
nano .env

# Sửa dòng này (thay YOUR_KEY_HERE):
DEFECTDOJO_API_KEY=YOUR_KEY_HERE
```

### 5. Restart Backend
```bash
docker compose restart backend celery
```

## 🧪 Test Hệ thống

### Test 1: Nmap Scan
```bash
curl -X POST http://localhost:8000/scan/nmap \
  -H "Content-Type: application/json" \
  -d '{
    "target": "scanme.nmap.org",
    "options": "-F"
  }'
```

### Test 2: ZAP Scan  
```bash
curl -X POST http://localhost:8000/scan/zap \
  -H "Content-Type: application/json" \
  -d '{
    "target": "http://testphp.vulnweb.com",
    "options": "passive"
  }'
```

### Test 3: Theo dõi Tiến độ
```bash
# Thay TASK_ID bằng ID từ response trên
curl http://localhost:8000/scan/status/TASK_ID
```

### Test 4: Xem Kết quả
```bash
curl http://localhost:8000/results?limit=10
```

## 📊 Xem Kết quả

### DefectDojo Dashboard
```
http://localhost:8080
Login: admin / Admin@123

Navigate to:
- Findings → View all findings
- Products → PTaaS Lab Project
```

### MinIO Storage
```
http://localhost:9001
Login: minioadmin / minioadmin

Bucket: ptaas
- Chứa tất cả scan results (XML, JSON)
```

### API Documentation
```
http://localhost:8000/docs
- Interactive Swagger UI
- Test API trực tiếp trong browser
```

## 🎯 Luồng Hoạt động Đầy đủ

```
1. User gửi request → POST /scan/nmap hoặc /scan/zap
2. Backend tạo Celery task → Đẩy vào Redis queue
3. Celery Worker nhận task → Bắt đầu xử lý
4. Scanner chạy (Nmap/ZAP) → Thu thập dữ liệu
5. Upload kết quả → MinIO (S3-compatible storage)
6. Import vào DefectDojo → Phân tích lỗ hổng
7. User lấy kết quả → GET /results
```

## 📝 Script Test Tự động

Chạy script test toàn diện:
```bash
cd ~/ptaas
chmod +x test_api.sh
./test_api.sh
```

## 🔧 Troubleshooting

### Kiểm tra Services
```bash
docker compose ps
```

### Xem Logs
```bash
# Backend
docker compose logs backend --tail=50 -f

# Celery Worker  
docker compose logs celery --tail=50 -f

# ZAP
docker compose logs zap --tail=50 -f
```

### Restart Tất cả
```bash
docker compose restart
```

### Stop/Start
```bash
docker compose down
docker compose up -d
```

## 🌐 Chuyển sang AWS

Khi sẵn sàng deploy production, chỉ cần đổi .env:

```bash
# Local
DB_HOST=postgres
S3_ENDPOINT=http://minio:9000
CELERY_BROKER_URL=redis://redis:6379/0

# AWS  
DB_HOST=ptaas-db.xyz.rds.amazonaws.com
S3_ENDPOINT=https://s3.amazonaws.com
CELERY_BROKER_URL=redis://elasticache.xyz.amazonaws.com:6379
```

→ **Code không cần sửa gì!**

## 📈 Bước Tiếp theo

- [ ] Thêm Authentication (JWT)
- [ ] Rate Limiting  
- [ ] Report Generation (PDF)
- [ ] Email/Slack Notifications
- [ ] Web Dashboard (Frontend)
- [ ] Kubernetes Deployment
- [ ] CI/CD Pipeline

---

**🎉 Chúc mừng! Hệ thống PTaaS của bạn đã sẵn sàng!**
