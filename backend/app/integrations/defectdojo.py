"""
DefectDojo API Client for PTaaS
"""
import requests
from typing import Optional, List, Dict, Any
import os
from io import BytesIO

class DefectDojoClient:
    """
    Client for interacting with DefectDojo API
    Supports both local and production environments via environment variables
    """
    
    def __init__(self):
        self.base_url = os.getenv('DEFECTDOJO_URL', 'http://nginx:8080')
        self.api_key = os.getenv('DEFECTDOJO_API_KEY')
        
        if not self.api_key:
            print("Warning: DEFECTDOJO_API_KEY not set")
        
        self.headers = {
            'Authorization': f'Token {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to DefectDojo API"""
        url = f"{self.base_url}/api/v2/{endpoint}"
        
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            print(f"[DefectDojo] API error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise
    
    def import_scan(
        self,
        file_content: bytes,
        filename: str,
        scan_type: str,
        engagement_name: str,
        product_name: str = "PTaaS Lab Project",
        auto_create: bool = True
    ) -> Dict[str, Any]:
        """
        Import scan results into DefectDojo
        
        Args:
            file_content: Scan file content as bytes
            filename: Name of the scan file
            scan_type: Type of scan (e.g., "Nmap Scan", "ZAP Scan")
            engagement_name: Name for the engagement
            product_name: Product name (will be created if doesn't exist)
            auto_create: Auto-create product and engagement if needed
            
        Returns:
            Import result from DefectDojo API
        """
        # Ensure product exists first
        self._ensure_product_exists(product_name)
        
        import_url = f"{self.base_url}/api/v2/import-scan/"
        
        # Prepare headers without Content-Type (let requests handle multipart)
        headers = {
            'Authorization': f'Token {self.api_key}'
        }
        
        # Prepare multipart form data
        files = {
            'file': (filename, BytesIO(file_content))
        }
        
        data = {
            'scan_type': scan_type,
            'product_name': product_name,
            'engagement_name': engagement_name,
            'auto_create_context': str(auto_create).lower(),
            'active': 'true',
            'verified': 'false',
            'close_old_findings': 'false'
        }
        
        try:
            response = requests.post(import_url, headers=headers, data=data, files=files)
            
            if response.status_code in [200, 201]:
                print(f"[DefectDojo] Imported {scan_type} successfully")
                return response.json()
            else:
                print(f"[DefectDojo] Import failed: {response.status_code}")
                print(f"Response: {response.text}")
                return {'error': response.text, 'status_code': response.status_code}
                
        except Exception as e:
            print(f"[DefectDojo] Import error: {e}")
            raise
    
    def _ensure_product_exists(self, product_name: str) -> Dict[str, Any]:
        """Create product if it doesn't exist"""
        try:
            # Check if product exists
            products = self._request('GET', f'products/?name={product_name}')
            if products.get('results'):
                print(f"Product '{product_name}' exists")
                return products['results'][0]
            
            # Get first available product type
            product_types = self._request('GET', 'product_types/')
            if not product_types.get('results'):
                # Create default product type if none exists
                pt_data = {'name': 'Security Testing', 'description': 'Security testing projects'}
                product_type = self._request('POST', 'product_types/', json=pt_data)
                prod_type_id = product_type['id']
                print(f"Created product type 'Security Testing' (ID: {prod_type_id})")
            else:
                prod_type_id = product_types['results'][0]['id']
                print(f"Using product type ID: {prod_type_id}")
            
            # Create product
            print(f"Creating product '{product_name}'...")
            product_data = {
                'name': product_name,
                'description': 'PTaaS Security Testing Project',
                'prod_type': prod_type_id
            }
            
            new_product = self._request('POST', 'products/', json=product_data)
            print(f"Created product '{product_name}' (ID: {new_product['id']})")
            return new_product
            
        except Exception as e:
            print(f"Warning: Could not ensure product exists: {e}")
            return {}
    
    def get_findings(
        self,
        product_name: Optional[str] = None,
        severity: Optional[str] = None,
        active: bool = True,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get findings from DefectDojo
        
        Args:
            product_name: Filter by product name
            severity: Filter by severity (Critical, High, Medium, Low, Info)
            active: Only active findings
            limit: Maximum number of results
            
        Returns:
            List of findings
        """
        params = {
            'limit': limit,
            'active': str(active).lower()
        }
        
        if product_name:
            # First, get product ID
            products = self._request('GET', f'products/?name={product_name}')
            if products.get('results'):
                params['test__engagement__product'] = products['results'][0]['id']
        
        if severity:
            params['severity'] = severity
        
        try:
            response = self._request('GET', 'findings/', params=params)
            findings = response.get('results', [])
            
            # Transform findings to match our ResultResponse model
            return [{
                'id': f['id'],
                'title': f['title'],
                'severity': f['severity'],
                'description': f.get('description'),
                'mitigation': f.get('mitigation'),
                'impact': f.get('impact'),
                'references': f.get('references'),
                'cve': f.get('cve'),
                'cvss_score': f.get('cvssv3_score'),
                'found_by': [str(fb) for fb in f.get('found_by', [])] if f.get('found_by') else [],
                'url': f.get('url'),
                'date': str(f.get('date')) if f.get('date') else None,
                'active': f.get('active', True),
                'verified': f.get('verified', False)
            } for f in findings]
            
        except Exception as e:
            print(f"[DefectDojo] Get findings error: {e}")
            return []
    
    def get_finding_detail(self, finding_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific finding"""
        try:
            finding = self._request('GET', f'findings/{finding_id}/')
            return {
                'id': finding['id'],
                'title': finding['title'],
                'severity': finding['severity'],
                'description': finding.get('description'),
                'mitigation': finding.get('mitigation'),
                'impact': finding.get('impact'),
                'references': finding.get('references'),
                'cve': finding.get('cve'),
                'cvss_score': finding.get('cvssv3_score'),
                'found_by': finding.get('found_by', []),
                'url': finding.get('url'),
                'date': finding.get('date'),
                'active': finding.get('active', True),
                'verified': finding.get('verified', False),
                'endpoints': finding.get('endpoints', []),
                'tags': finding.get('tags', [])
            }
        except Exception as e:
            print(f"[DefectDojo] Get finding detail error: {e}")
            return None
    
    def get_products(self) -> List[Dict[str, Any]]:
        """Get all products"""
        try:
            response = self._request('GET', 'products/')
            return response.get('results', [])
        except Exception as e:
            print(f"[DefectDojo] Get products error: {e}")
            return []

    def get_engagements(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get engagements/tests for dashboard/history"""
        try:
            response = self._request('GET', 'engagements/', params={'limit': limit})
            return response.get('results', [])
        except Exception as e:
            print(f"[DefectDojo] Get engagements error: {e}")
            return []

    def list_findings_raw(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Return raw findings payload (used by frontend to keep test info)"""
        try:
            data = self._request('GET', 'findings/', params={'limit': limit, 'offset': offset})
            return data.get('results', [])
        except Exception as e:
            print(f"[DefectDojo] List findings raw error: {e}")
            return []

    def list_engagements_raw(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Return raw engagements payload"""
        try:
            data = self._request('GET', 'engagements/', params={'limit': limit, 'offset': offset})
            return data.get('results', [])
        except Exception as e:
            print(f"[DefectDojo] List engagements raw error: {e}")
            return []

    def get_tests(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all tests with details"""
        try:
            response = self._request('GET', 'tests/', params={'limit': limit})
            return response.get('results', [])
        except Exception as e:
            print(f"[DefectDojo] Get tests error: {e}")
            return []

    def get_test_detail(self, test_id: int) -> Optional[Dict[str, Any]]:
        """Get test detail by ID"""
        try:
            return self._request('GET', f'tests/{test_id}/')
        except Exception as e:
            print(f"[DefectDojo] Get test detail error: {e}")
            return None
    
    def get_test_file(self, test_id: int) -> Optional[bytes]:
        """
        Try to download raw scan file from DefectDojo test
        DefectDojo may store file attachments in test files endpoint
        Falls back to searching MinIO for matching raw files
        """
        try:
            # First, check if test has file_upload field or attachments
            test = self.get_test_detail(test_id)
            if not test:
                return None
            
            # DefectDojo might have files in separate endpoint
            try:
                files_response = self._request('GET', f'tests/{test_id}/files/')
                if files_response and 'results' in files_response and len(files_response['results']) > 0:
                    # Try to download the first file
                    file_obj = files_response['results'][0]
                    if 'file' in file_obj:
                        file_url = file_obj['file']
                        # Download the file
                        headers = {'Authorization': f'Token {self.api_key}'}
                        response = requests.get(file_url, headers=headers)
                        if response.status_code == 200:
                            return response.content
            except:
                # DefectDojo may not have files endpoint, continue
                pass
            
            # Fallback: Try to find raw file in MinIO by searching for test-related patterns
            # This requires importing StorageClient, but avoid circular imports
            # Instead, return None and let the endpoint handle MinIO fallback
            return None
        except Exception as e:
            print(f"[DefectDojo] Get test file error: {e}")
            return None
    
    def create_product(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new product"""
        data = {
            'name': name,
            'description': description,
            'prod_type': 1  # Default product type
        }
        
        try:
            return self._request('POST', 'products/', json=data)
        except Exception as e:
            print(f"[DefectDojo] Create product error: {e}")
            raise
