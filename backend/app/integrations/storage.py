"""
MinIO/S3 Storage Client for PTaaS
"""
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import os
from io import BytesIO
from typing import Optional

class StorageClient:
    """
    Unified storage client supporting both MinIO (local) and AWS S3 (production)
    Configuration is environment-based for seamless local-to-cloud transition
    """
    
    def __init__(self):
        self.endpoint_url = os.getenv('S3_ENDPOINT')
        self.bucket_name = os.getenv('S3_BUCKET', 'ptaas')
        self.access_key = os.getenv('S3_ACCESS_KEY')
        self.secret_key = os.getenv('S3_SECRET_KEY')
        
        # Initialize S3 client
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'  # Required for MinIO compatibility
        )
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            print(f"Bucket '{self.bucket_name}' exists")
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket_name)
                print(f"Created bucket '{self.bucket_name}'")
            except Exception as e:
                print(f"Warning: Could not create bucket: {e}")
    
    def upload(self, file_content: bytes, filename: str, content_type: str = 'application/octet-stream') -> str:
        """
        Upload file to storage
        
        Args:
            file_content: File content as bytes
            filename: Name of the file
            content_type: MIME type of the file
            
        Returns:
            URL or path to the uploaded file
        """
        try:
            # Convert bytes to BytesIO if needed
            if isinstance(file_content, bytes):
                file_obj = BytesIO(file_content)
            else:
                file_obj = file_content
            
            # Upload to S3/MinIO
            self.client.upload_fileobj(
                file_obj,
                self.bucket_name,
                filename,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Generate URL
            if 'minio' in self.endpoint_url.lower():
                # MinIO local URL
                url = f"{self.endpoint_url}/{self.bucket_name}/{filename}"
            else:
                # AWS S3 URL
                url = f"https://{self.bucket_name}.s3.amazonaws.com/{filename}"
            
            print(f"[Storage] Uploaded: {filename}")
            return url
            
        except Exception as e:
            print(f"[Storage] Upload failed: {e}")
            raise
    
    def download(self, filename: str) -> bytes:
        """Download file from storage"""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=filename)
            return response['Body'].read()
        except Exception as e:
            print(f"[Storage] Download failed: {e}")
            raise
    
    def list_files(self, prefix: str = '') -> list:
        """List files in bucket with optional prefix filter"""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except Exception as e:
            print(f"[Storage] List failed: {e}")
            return []
    
    def delete(self, filename: str) -> bool:
        """Delete file from storage"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=filename)
            print(f"[Storage] Deleted: {filename}")
            return True
        except Exception as e:
            print(f"[Storage] Delete failed: {e}")
            return False
