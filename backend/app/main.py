# FastAPI Backend for PTaaS
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, List, Dict
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Import tasks
from .tasks import scan_with_nmap, scan_with_zap, scan_with_sqlmap
from .models import ScanRequest, ScanResponse, ResultResponse
from .integrations.defectdojo import DefectDojoClient

app = FastAPI(
    title="PTaaS API Gateway",
    description="Penetration Testing as a Service Platform",
    version="1.0.0"
)

# In-memory registry of active scans (task_id -> metadata)
ACTIVE_SCANS: Dict[str, Dict] = {}
TASK_LOG: List[Dict] = []

def _find_task_log(task_id: str) -> Optional[Dict]:
    for entry in TASK_LOG:
        if entry.get("task_id") == task_id:
            return entry
    return None

def _upsert_task_log(task_id: str, state: str, result: Optional[Dict] = None):
    meta = ACTIVE_SCANS.get(task_id, {})
    entry = _find_task_log(task_id) or {
        "task_id": task_id,
        "scan_type": meta.get("scan_type"),
        "target": meta.get("target"),
        "created": meta.get("created", datetime.utcnow().isoformat()),
    }
    entry["state"] = state
    entry["status"] = "success" if state == "SUCCESS" else ("failure" if state == "FAILURE" else state.lower())
    entry["timestamp"] = datetime.utcnow().isoformat()
    if result and isinstance(result, dict):
        entry["storage_url"] = result.get("storage_url")
        entry["filename"] = result.get("filename")
        dojo = result.get("dojo_import") or {}
        if isinstance(dojo, dict):
            entry["dojo_test_id"] = dojo.get("test_id")
            entry["engagement_id"] = dojo.get("engagement_id")
            entry["product_id"] = dojo.get("product_id")
    # Insert or update
    if not _find_task_log(task_id):
        TASK_LOG.append(entry)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "PTaaS API Gateway",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "redis": os.getenv("CELERY_BROKER_URL"),
        "defectdojo": os.getenv("DEFECTDOJO_URL"),
        "storage": os.getenv("S3_ENDPOINT")
    }

@app.post("/scan/nmap", response_model=ScanResponse)
async def scan_nmap(request: ScanRequest):
    """
    Start Nmap scan for target IP/CIDR
    """
    task = scan_with_nmap.delay(
        target=request.target,
        options=request.options or "-sV -sC"
    )
    # Track active scan
    ACTIVE_SCANS[task.id] = {
        "task_id": task.id,
        "scan_type": "nmap",
        "target": request.target,
        "state": "QUEUED",
        "progress": 0,
        "status": "Queued"
    }
    
    return ScanResponse(
        task_id=task.id,
        scan_type="nmap",
        target=request.target,
        status="queued",
        message=f"Nmap scan queued for {request.target}"
    )

@app.post("/scan/zap", response_model=ScanResponse)
async def scan_zap(request: ScanRequest):
    """
    Start OWASP ZAP scan for target URL
    """
    task = scan_with_zap.delay(
        target_url=request.target,
        scan_type=request.options or "active"
    )
    # Track active scan
    ACTIVE_SCANS[task.id] = {
        "task_id": task.id,
        "scan_type": "zap",
        "target": request.target,
        "state": "QUEUED",
        "progress": 0,
        "status": "Queued"
    }
    
    return ScanResponse(
        task_id=task.id,
        scan_type="zap",
        target=request.target,
        status="queued",
        message=f"ZAP scan queued for {request.target}"
    )

@app.post("/scan/sqlmap", response_model=ScanResponse)
async def scan_sqlmap(request: ScanRequest):
    """
    Start SQLMap scan for target URL
    """
    task = scan_with_sqlmap.delay(
        target_url=request.target,
        options=request.options or "--batch --level=1 --risk=1"
    )
    # Track active scan
    ACTIVE_SCANS[task.id] = {
        "task_id": task.id,
        "scan_type": "sqlmap",
        "target": request.target,
        "state": "QUEUED",
        "progress": 0,
        "status": "Queued"
    }
    
    return ScanResponse(
        task_id=task.id,
        scan_type="sqlmap",
        target=request.target,
        status="queued",
        message=f"SQLMap scan queued for {request.target}"
    )

@app.get("/scan/status/{task_id}")
async def get_scan_status(task_id: str):
    """
    Get status of a scan task
    """
    from .celery_app import celery_app
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id, app=celery_app)
    
    if task.state == 'PENDING':
        response = {
            'task_id': task_id,
            'state': task.state,
            'status': 'Task is waiting in queue...'
        }
    elif task.state == 'STARTED':
        response = {
            'task_id': task_id,
            'state': task.state,
            'status': 'Task is currently running...',
            'progress': task.info.get('progress', 0) if task.info else 0
        }
    elif task.state == 'SUCCESS':
        response = {
            'task_id': task_id,
            'state': task.state,
            'status': 'Task completed successfully',
            'result': task.result
        }
        try:
            _upsert_task_log(task_id, 'SUCCESS', task.result)
        except Exception as _:
            pass
    elif task.state == 'FAILURE':
        response = {
            'task_id': task_id,
            'state': task.state,
            'status': str(task.info),
            'error': str(task.info)
        }
        try:
            _upsert_task_log(task_id, 'FAILURE')
        except Exception as _:
            pass
    else:
        response = {
            'task_id': task_id,
            'state': task.state,
            'status': str(task.info)
        }
    
    return response

@app.get("/scan/active")
async def list_active_scans():
    """Return current active scans with live status updates."""
    from .celery_app import celery_app
    from celery.result import AsyncResult

    updated: List[Dict] = []
    remove_keys: List[str] = []

    # Create snapshot to avoid dict size change during iteration
    scan_items = list(ACTIVE_SCANS.items())
    
    for task_id, meta in scan_items:
        try:
            task = AsyncResult(task_id, app=celery_app)
            state = task.state
            progress = 0
            status_msg = meta.get("status", "")
            
            if state == 'STARTED':
                if isinstance(task.info, dict):
                    progress = task.info.get('progress', 0)
                    status_msg = task.info.get('status', 'Running')
            elif state == 'SUCCESS':
                # Mark for cleanup after returning once
                remove_keys.append(task_id)
                status_msg = 'Completed'
            elif state == 'FAILURE':
                remove_keys.append(task_id)
                status_msg = 'Failed'

            updated.append({
                "task_id": task_id,
                "scan_type": meta.get("scan_type"),
                "target": meta.get("target"),
                "state": state,
                "progress": progress,
                "status": status_msg
            })
        except Exception as e:
            print(f"Error processing task {task_id}: {e}")
            remove_keys.append(task_id)

    # Cleanup finished tasks from registry
    for k in remove_keys:
        ACTIVE_SCANS.pop(k, None)

    return updated

@app.get("/scan/completed")
async def list_completed_scans():
    """Return completed/failed scans recorded in TASK_LOG."""
    # Return newest first
    return sorted(TASK_LOG, key=lambda e: e.get("timestamp", e.get("created", "")), reverse=True)

@app.get("/storage/raw/{task_id}")
async def download_raw_by_task(task_id: str):
    """Stream raw scan result from MinIO for a given task_id."""
    from fastapi.responses import StreamingResponse
    import re

    entry = _find_task_log(task_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Task not found in log")
    storage_url = entry.get("storage_url")
    if not storage_url:
        raise HTTPException(status_code=404, detail="No storage_url for this task")

    # Expect format http://minio:9000/<bucket>/<key>
    m = re.match(r"https?://[^/]+/(.*?)/(.*)", storage_url)
    if not m:
        raise HTTPException(status_code=400, detail="Invalid storage_url format")
    bucket, key = m.group(1), m.group(2)

    try:
        import boto3
        from botocore.exceptions import ClientError
        s3_client = boto3.client('s3', 
            endpoint_url=os.getenv("S3_ENDPOINT"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY")
        )
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        content_type = 'application/xml' if key.endswith('.xml') else 'text/plain'
        return StreamingResponse(obj['Body'], media_type=content_type)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")

@app.get("/results", response_model=List[ResultResponse])
async def get_results(
    product: Optional[str] = None,
    limit: int = 10
):
    """
    Get scan results from DefectDojo (simplified model)
    """
    dojo_client = DefectDojoClient()
    findings = dojo_client.get_findings(product_name=product, limit=limit)
    return findings

@app.get("/results/{finding_id}")
async def get_result_detail(finding_id: int):
    """
    Get detailed information about a specific finding
    """
    dojo_client = DefectDojoClient()
    finding = dojo_client.get_finding_detail(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding

@app.get("/dojo/findings")
async def proxy_dojo_findings(limit: int = 100, offset: int = 0):
    """Proxy raw findings from DefectDojo to avoid browser CORS issues"""
    dojo_client = DefectDojoClient()
    return dojo_client.list_findings_raw(limit=limit, offset=offset)

@app.get("/dojo/engagements")
async def proxy_dojo_engagements(limit: int = 100, offset: int = 0):
    """Proxy engagements from DefectDojo for dashboard/history"""
    dojo_client = DefectDojoClient()
    return dojo_client.list_engagements_raw(limit=limit, offset=offset)

@app.get("/dojo/products")
async def proxy_dojo_products(limit: int = 100, offset: int = 0):
    dojo_client = DefectDojoClient()
    data = dojo_client.get_products()
    return data

@app.get("/dojo/tests")
async def proxy_dojo_tests(limit: int = 1000):
    """Proxy tests from DefectDojo for mapping test IDs to scan info"""
    dojo_client = DefectDojoClient()
    return dojo_client.get_tests(limit=limit)

@app.get("/dojo/tests/{test_id}")
async def proxy_dojo_test_detail(test_id: int):
    """Get test detail by ID"""
    dojo_client = DefectDojoClient()
    test = dojo_client.get_test_detail(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test

@app.get("/dojo/tests/{test_id}/raw")
async def download_dojo_test_raw(test_id: int):
    """Download raw scan file for DefectDojo test"""
    from .integrations.storage import StorageClient
    
    dojo_client = DefectDojoClient()
    
    # Try to get raw file from DefectDojo first
    raw_data = dojo_client.get_test_file(test_id)
    if raw_data:
        return StreamingResponse(
            iter([raw_data]),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="test_{test_id}_raw.xml"'}
        )
    
    # Fallback: Try MinIO - search for files matching test_id or target pattern
    storage = StorageClient()
    
    # Get test info to search by target name
    test = dojo_client.get_test_detail(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # List files in MinIO and try to find matching scan results
    # Look for files created around test creation time with similar scan type
    all_files = storage.list_files()
    
    # Filter by scan type pattern (nmap_*, zap_*, sqlmap_*)
    scan_type = test.get('scan_type', '').lower()
    matching_files = []
    
    if 'nmap' in scan_type:
        matching_files = [f for f in all_files if 'nmap' in f.lower()]
    elif 'zap' in scan_type:
        matching_files = [f for f in all_files if 'zap' in f.lower()]
    elif 'sqlmap' in scan_type:
        matching_files = [f for f in all_files if 'sqlmap' in f.lower()]
    
    if matching_files:
        # Try most recent file of this type
        matching_files.sort(reverse=True)
        filename = matching_files[0]
        try:
            raw_data = storage.download(filename)
            return StreamingResponse(
                iter([raw_data]),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
        except:
            pass
    
    # No raw file found
    raise HTTPException(status_code=404, detail="Raw file not found in MinIO or DefectDojo")

@app.get("/results/{task_id}/download")
async def download_raw_results(task_id: str):
    """Download raw scan results from MinIO (placeholder)"""
    # This would fetch from MinIO based on task_id
    # For now, return error since we need MinIO integration
    raise HTTPException(status_code=501, detail="Raw download not yet implemented")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )
