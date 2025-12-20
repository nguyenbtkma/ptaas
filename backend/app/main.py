# FastAPI Backend for PTaaS
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Import tasks
from .tasks import scan_with_nmap, scan_with_zap, scan_with_sqlmap
from .models import ScanRequest, ScanResponse, ResultResponse

app = FastAPI(
    title="PTaaS API Gateway",
    description="Penetration Testing as a Service Platform",
    version="1.0.0"
)

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
    elif task.state == 'FAILURE':
        response = {
            'task_id': task_id,
            'state': task.state,
            'status': str(task.info),
            'error': str(task.info)
        }
    else:
        response = {
            'task_id': task_id,
            'state': task.state,
            'status': str(task.info)
        }
    
    return response

@app.get("/results", response_model=List[ResultResponse])
async def get_results(
    product: Optional[str] = None,
    limit: int = 10
):
    """
    Get scan results from DefectDojo
    """
    from .integrations.defectdojo import DefectDojoClient
    
    dojo_client = DefectDojoClient()
    findings = dojo_client.get_findings(product_name=product, limit=limit)
    
    return findings

@app.get("/results/{finding_id}")
async def get_result_detail(finding_id: int):
    """
    Get detailed information about a specific finding
    """
    from .integrations.defectdojo import DefectDojoClient
    
    dojo_client = DefectDojoClient()
    finding = dojo_client.get_finding_detail(finding_id)
    
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    return finding

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )
