"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ScanType(str, Enum):
    NMAP = "nmap"
    ZAP = "zap"
    SQLMAP = "sqlmap"

class ScanStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ScanRequest(BaseModel):
    """Request model for starting a scan"""
    target: str = Field(..., description="Target URL or IP address")
    options: Optional[str] = Field(None, description="Additional scan options")
    
    @validator('target')
    def validate_target(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Target cannot be empty')
        return v.strip()

class ScanResponse(BaseModel):
    """Response model for scan initiation"""
    task_id: str = Field(..., description="Celery task ID")
    scan_type: str = Field(..., description="Type of scan")
    target: str = Field(..., description="Target being scanned")
    status: str = Field(..., description="Current status")
    message: str = Field(..., description="Status message")

class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"

class ResultResponse(BaseModel):
    """Response model for vulnerability findings"""
    id: int
    title: str
    severity: str
    description: Optional[str] = None
    mitigation: Optional[str] = None
    impact: Optional[str] = None
    references: Optional[str] = None
    cve: Optional[str] = None
    cvss_score: Optional[float] = None
    found_by: Optional[List[Any]] = None  # Can be string or int from DefectDojo
    url: Optional[str] = None
    date: Optional[str] = None  # Use string instead of datetime for flexibility
    active: bool = True
    verified: bool = False
    
    class Config:
        from_attributes = True
