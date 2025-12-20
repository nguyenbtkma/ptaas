import os
import docker
import boto3
import requests
import time
from fastapi import FastAPI, BackgroundTasks
from io import BytesIO
from dotenv import load_dotenv

# 1. Nạp .env ngay lập tức
load_dotenv(dotenv_path="../.env")

app = FastAPI(title="PTaaS Core Engine")

# 2. Khởi tạo Clients
docker_client = docker.from_env()
s3_client = boto3.client('s3', 
    endpoint_url=os.getenv("S3_ENDPOINT"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY")
)

def upload_to_s3_and_dojo(file_content, file_name, scan_type, target):
    """Hàm dùng chung để đẩy data lên MinIO và Dojo"""
    # Đẩy lên MinIO (S3)
    s3_client.upload_fileobj(BytesIO(file_content), os.getenv("S3_BUCKET"), file_name)
    print(f"📦 [MinIO] Đã lưu trữ: {file_name}")

    # Đẩy vào DefectDojo
    import_url = f"{os.getenv('DEFECTDOJO_URL')}/api/v2/import-scan/"
    headers = {"Authorization": f"Token {os.getenv('DEFECTDOJO_API_KEY')}"}
    files = {'file': (file_name, file_content)}
    data = {
        "scan_type": scan_type,
        "product_name": "PTaaS Lab Project",
        "engagement_name": f"Scan {target} - {time.strftime('%Y-%m-%d')}",
        "auto_create_context": "true"
    }
    res = requests.post(import_url, headers=headers, data=data, files=files)
    if res.status_code == 201:
        print(f"🚀 [Dojo] Import thành công kết quả {scan_type}")
    else:
        print(f"❌ [Dojo] Lỗi: {res.text}")

def process_nmap(target):
    container = docker_client.containers.get(os.getenv("CONTAINER_NMAP"))
    # Chạy nmap xuất XML ra stdout (-)
    result = container.exec_run(f"nmap -oX - {target}")
    upload_to_s3_and_dojo(result.output, f"nmap_{target}.xml", "Nmap Scan", target)

def process_zap(target_url):
    # Gọi API của ZAP container để chạy Active Scan
    zap_base = os.getenv("ZAP_URL")
    print(f"📡 [ZAP] Đang quét: {target_url}")
    
    # 1. Mở URL
    requests.get(f"{zap_base}/JSON/core/action/accessUrl/?url={target_url}")
    # 2. Quét lỗ hổng (Active Scan)
    scan_id_res = requests.get(f"{zap_base}/JSON/ascan/action/scan/?url={target_url}")
    scan_id = scan_id_res.json().get("scan")
    
    # 3. Đợi quét xong (Check progress)
    while True:
        progress = requests.get(f"{zap_base}/JSON/ascan/view/status/?scanId={scan_id}").json()["status"]
        if int(progress) >= 100: break
        time.sleep(5)
    
    # 4. Lấy Report JSON
    report_res = requests.get(f"{zap_base}/OTHER/core/other/jsonreport/")
    upload_to_s3_and_dojo(report_res.content, f"zap_{int(time.time())}.json", "ZAP Scan", target_url)

@app.post("/scan")
async def start_scan(type: str, target: str, background_tasks: BackgroundTasks):
    if type.lower() == "nmap":
        background_tasks.add_task(process_nmap, target)
    elif type.lower() == "zap":
        background_tasks.add_task(process_zap, target)
    return {"message": f"Đã bắt đầu quét {type}", "target": target}
