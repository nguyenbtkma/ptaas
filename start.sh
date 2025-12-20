#!/bin/bash

# PTaaS Quick Start Script
# Tự động setup và khởi chạy hệ thống

echo "PTaaS Quick Start"
echo "===================="

# 1. Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker chưa được cài đặt"
    exit 1
fi

echo "Docker đã cài đặt"

# 2. Copy .env nếu chưa có
if [ ! -f .env ]; then
    echo "Tạo file .env từ template..."
    cp .env.example .env
    echo "Lưu ý: Bạn cần cập nhật DEFECTDOJO_API_KEY sau khi khởi động"
else
    echo "File .env đã tồn tại"
fi

# 3. Khởi động services
echo ""
echo "Khởi động Docker containers..."
docker-compose up -d

echo ""
echo "Đợi services khởi động (30s)..."
sleep 30

# 4. Kiểm tra health
echo ""
echo "Kiểm tra services..."

services=("postgres" "redis" "minio" "nginx" "zap" "nmap" "sqlmap")
for service in "${services[@]}"; do
    if docker ps | grep -q "ptaas-$service"; then
        echo "$service đang chạy"
    else
        echo "$service không chạy"
    fi
done

# 5. Hiển thị URLs
echo ""
echo "Services URLs:"
echo "===================="
echo "DefectDojo:  http://localhost:8080"
echo "             Login: admin / Admin@123"
echo ""
echo "MinIO:       http://localhost:9001"
echo "             Login: minioadmin / minioadmin"
echo ""
echo "Backend API: http://localhost:8000"
echo "             Docs: http://localhost:8000/docs"
echo ""
echo "ZAP Proxy:   http://localhost:8090"
echo ""

# 6. Hướng dẫn tiếp theo
echo "Bước tiếp theo:"
echo "===================="
echo "1. Truy cập DefectDojo: http://localhost:8080"
echo "2. Login với admin / Admin@123"
echo "3. Vào Configuration → API v2 Key"
echo "4. Tạo API key mới"
echo "5. Copy key vào file .env (DEFECTDOJO_API_KEY=...)"
echo "6. Restart backend: docker-compose restart backend celery"
echo ""
echo "Test API:"
echo "curl -X POST http://localhost:8000/scan/nmap \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"target\": \"scanme.nmap.org\"}'"
echo ""
echo "Setup hoàn tất!"
