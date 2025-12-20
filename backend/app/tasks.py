"""
Celery tasks for PTaaS scanners
"""
from celery import Task
from .celery_app import celery_app
import docker
import requests
import time
import os
from .integrations.storage import StorageClient
from .integrations.defectdojo import DefectDojoClient

# Initialize clients
docker_client = docker.from_env()
storage_client = StorageClient()
dojo_client = DefectDojoClient()

class ScanTask(Task):
    """Base task with common functionality"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        print(f'Task {task_id} failed: {exc}')
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        print(f'Task {task_id} completed successfully')

@celery_app.task(base=ScanTask, bind=True, name='app.tasks.scan_with_nmap')
def scan_with_nmap(self, target: str, options: str = "-sV -sC"):
    """
    Execute Nmap scan in container and upload results
    """
    self.update_state(state='STARTED', meta={'progress': 0, 'status': 'Initializing Nmap scan...'})
    
    try:
        # Get Nmap container
        container_name = os.getenv('NMAP_CONTAINER', 'ptaas-nmap')
        
        self.update_state(state='STARTED', meta={'progress': 20, 'status': f'Scanning {target}...'})
        
        # Run Nmap scan (output to XML)
        container = docker_client.containers.get(container_name)
        command = f"nmap {options} -oX - {target}"
        result = container.exec_run(command)
        
        if result.exit_code != 0:
            raise Exception(f"Nmap scan failed: {result.output.decode()}")
        
        scan_output = result.output
        
        self.update_state(state='STARTED', meta={'progress': 60, 'status': 'Uploading to storage...'})
        
        # Upload to MinIO/S3
        filename = f"nmap_{target.replace('/', '_')}_{int(time.time())}.xml"
        storage_url = storage_client.upload(scan_output, filename, content_type='application/xml')
        
        self.update_state(state='STARTED', meta={'progress': 80, 'status': 'Importing to DefectDojo...'})
        
        # Import to DefectDojo
        dojo_result = dojo_client.import_scan(
            file_content=scan_output,
            filename=filename,
            scan_type="Nmap Scan",
            engagement_name=f"Nmap Scan - {target}",
            product_name="PTaaS Lab Project"
        )
        
        self.update_state(state='STARTED', meta={'progress': 100, 'status': 'Completed'})
        
        return {
            'status': 'success',
            'target': target,
            'storage_url': storage_url,
            'dojo_import': dojo_result,
            'filename': filename
        }
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(base=ScanTask, bind=True, name='app.tasks.scan_with_zap')
def scan_with_zap(self, target_url: str, scan_type: str = "active"):
    """
    Execute OWASP ZAP scan and upload results
    ZAP Container must be running with API enabled
    """
    self.update_state(state='STARTED', meta={'progress': 0, 'status': 'Initializing ZAP scan...'})
    
    try:
        zap_base_url = os.getenv('ZAP_URL', 'http://zap:8080')
        zap_api_key = os.getenv('ZAP_API_KEY', 'changeme')
        
        # ZAP API endpoints
        def zap_api(endpoint):
            url = f"{zap_base_url}/{endpoint}"
            if '?' in url:
                url += f"&apikey={zap_api_key}"
            else:
                url += f"?apikey={zap_api_key}"
            return url
        
        self.update_state(state='STARTED', meta={'progress': 10, 'status': f'Accessing URL: {target_url}'})
        
        # 1. Access the target URL (Spider)
        requests.get(zap_api(f"JSON/core/action/accessUrl/?url={target_url}"))
        time.sleep(2)
        
        # 2. Start Spider scan
        spider_response = requests.get(zap_api(f"JSON/spider/action/scan/?url={target_url}"))
        spider_id = spider_response.json().get('scan')
        
        self.update_state(state='STARTED', meta={'progress': 20, 'status': 'Spidering website...'})
        
        # Wait for spider to complete
        while True:
            spider_status = requests.get(zap_api(f"JSON/spider/view/status/?scanId={spider_id}"))
            progress = int(spider_status.json().get('status', 0))
            self.update_state(state='STARTED', meta={'progress': 20 + (progress * 0.3), 'status': f'Spider: {progress}%'})
            if progress >= 100:
                break
            time.sleep(3)
        
        # 3. Start Active Scan (if requested)
        if scan_type.lower() == "active":
            self.update_state(state='STARTED', meta={'progress': 50, 'status': 'Starting active scan...'})
            
            ascan_response = requests.get(zap_api(f"JSON/ascan/action/scan/?url={target_url}"))
            ascan_id = ascan_response.json().get('scan')
            
            # Wait for active scan to complete
            while True:
                ascan_status = requests.get(zap_api(f"JSON/ascan/view/status/?scanId={ascan_id}"))
                progress = int(ascan_status.json().get('status', 0))
                self.update_state(state='STARTED', meta={'progress': 50 + (progress * 0.3), 'status': f'Active Scan: {progress}%'})
                if progress >= 100:
                    break
                time.sleep(5)
        
        self.update_state(state='STARTED', meta={'progress': 80, 'status': 'Generating report...'})
        
        # 4. Get JSON report
        report_response = requests.get(zap_api("OTHER/core/other/jsonreport/"))
        scan_output = report_response.content
        
        self.update_state(state='STARTED', meta={'progress': 85, 'status': 'Uploading to storage...'})
        
        # Upload to MinIO/S3
        filename = f"zap_{target_url.replace('://', '_').replace('/', '_')}_{int(time.time())}.json"
        storage_url = storage_client.upload(scan_output, filename, content_type='application/json')
        
        self.update_state(state='STARTED', meta={'progress': 90, 'status': 'Importing to DefectDojo...'})
        
        # Import to DefectDojo
        dojo_result = dojo_client.import_scan(
            file_content=scan_output,
            filename=filename,
            scan_type="ZAP Scan",
            engagement_name=f"ZAP {scan_type.title()} Scan - {target_url}",
            product_name="PTaaS Lab Project"
        )
        
        self.update_state(state='STARTED', meta={'progress': 100, 'status': 'Completed'})
        
        return {
            'status': 'success',
            'target': target_url,
            'scan_type': scan_type,
            'storage_url': storage_url,
            'dojo_import': dojo_result,
            'filename': filename
        }
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(base=ScanTask, bind=True, name='app.tasks.scan_with_sqlmap')
def scan_with_sqlmap(self, target_url: str, options: str = "--batch --level=1 --risk=1"):
    """
    Execute SQLMap scan in container and upload results
    """
    self.update_state(state='STARTED', meta={'progress': 0, 'status': 'Initializing SQLMap scan...'})
    
    try:
        # Get SQLMap container
        container_name = os.getenv('SQLMAP_CONTAINER', 'ptaas-sqlmap')
        
        self.update_state(state='STARTED', meta={'progress': 20, 'status': f'Scanning {target_url}...'})
        
        # Run SQLMap
        container = docker_client.containers.get(container_name)
        command = f"sqlmap -u {target_url} {options} --output-dir=/tmp/sqlmap --json"
        result = container.exec_run(command)
        
        scan_output = result.output
        
        self.update_state(state='STARTED', meta={'progress': 70, 'status': 'Uploading results...'})
        
        # Upload to MinIO/S3
        filename = f"sqlmap_{target_url.replace('://', '_').replace('/', '_')}_{int(time.time())}.txt"
        storage_url = storage_client.upload(scan_output, filename, content_type='text/plain')
        
        self.update_state(state='STARTED', meta={'progress': 100, 'status': 'Completed'})
        
        return {
            'status': 'success',
            'target': target_url,
            'storage_url': storage_url,
            'filename': filename
        }
        
    except docker.errors.NotFound:
        raise Exception(f"SQLMap container '{container_name}' not found")
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
