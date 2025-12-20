import os
from dotenv import load_dotenv

# Nạp file .env từ thư mục cha
load_dotenv(dotenv_path="../.env")

def test_config():
    print("--- KIỂM TRA BIẾN MÔI TRƯỜNG ---")
    services = {
        "DefectDojo URL": os.getenv("DEFECTDOJO_URL"),
        "API Key": os.getenv("DEFECTDOJO_API_KEY")[:5] + "******", # Chỉ hiện 5 ký tự đầu bảo mật
        "MinIO End": os.getenv("S3_ENDPOINT"),
        "Nmap Container": os.getenv("CONTAINER_NMAP")
    }
    
    for name, value in services.items():
        if value:
            print(f"OK - {name}: {value}")
        else:
            print(f"MISSING - {name}: CHƯA CÓ (Kiểm tra lại file .env)")

if __name__ == "__main__":
    test_config()
