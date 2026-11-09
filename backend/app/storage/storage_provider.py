import os
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.core.config import settings
from app.core.logging import logger


class BaseStorageProvider(ABC):
    """Abstract interface for document object storage (Local filesystem or Cloud S3/R2/MinIO)."""

    @abstractmethod
    def save_file(self, file_bytes: bytes, filename: str) -> str:
        """Persists file bytes and returns storage key or absolute path."""
        pass

    @abstractmethod
    def get_file_bytes(self, storage_path: str) -> bytes:
        """Retrieves raw file bytes."""
        pass

    @abstractmethod
    def get_local_path(self, storage_path: str) -> Optional[Path]:
        """Returns local filesystem Path if stored locally, or None if remote object."""
        pass

    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """Removes document from persistent storage."""
        pass

    @abstractmethod
    def generate_download_url(self, storage_path: str, doc_id: str, expiry_seconds: int = 3600) -> str:
        """Generates authenticated download URL (pre-signed S3 URL or API endpoint)."""
        pass


class LocalStorageProvider(BaseStorageProvider):
    """Local Windows 11 filesystem storage provider."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or settings.resolved_storage_path
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_bytes: bytes, filename: str) -> str:
        ext = Path(filename).suffix.lower() or ".pdf"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        target_path = self.base_dir / unique_name
        with open(target_path, "wb") as f:
            f.write(file_bytes)
        logger.debug(f"Saved document locally: {target_path}")
        return str(target_path.resolve())

    def get_file_bytes(self, storage_path: str) -> bytes:
        p = Path(storage_path)
        if not p.is_absolute():
            p = self.base_dir / storage_path
        with open(p, "rb") as f:
            return f.read()

    def get_local_path(self, storage_path: str) -> Optional[Path]:
        p = Path(storage_path)
        if not p.is_absolute():
            p = self.base_dir / storage_path
        return p if p.exists() else None

    def delete_file(self, storage_path: str) -> bool:
        p = Path(storage_path)
        if not p.is_absolute():
            p = self.base_dir / storage_path
        if p.exists():
            try:
                os.remove(p)
                return True
            except OSError as e:
                logger.error(f"Error removing local file {p}: {e}")
                return False
        return False

    def generate_download_url(self, storage_path: str, doc_id: str, expiry_seconds: int = 3600) -> str:
        return f"{settings.SERVER_PUBLIC_URL}/api/v1/documents/{doc_id}/download"


class S3StorageProvider(BaseStorageProvider):
    """
    Cloud Object Storage provider compatible with AWS S3, Cloudflare R2, and MinIO.
    Generates time-limited pre-signed URLs for outbound Windows Print Agent retrieval.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None
    ):
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key = access_key or settings.S3_ACCESS_KEY
        self.secret_key = secret_key or settings.S3_SECRET_KEY
        self.region = region or settings.S3_REGION_NAME
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region
                )
            except ImportError:
                logger.warning("boto3 is not installed. S3StorageProvider is operating in simulated cloud mode.")
                self._client = None
        return self._client

    def save_file(self, file_bytes: bytes, filename: str) -> str:
        ext = Path(filename).suffix.lower() or ".pdf"
        key = f"documents/{uuid.uuid4().hex}{ext}"
        client = self._get_client()
        if client:
            client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_bytes,
                ContentType="application/pdf"
            )
            logger.info(f"Uploaded document to S3 bucket '{self.bucket_name}': {key}")
        else:
            logger.info(f"[SIMULATED S3] Uploaded {len(file_bytes)} bytes to key {key}")
        return key

    def get_file_bytes(self, storage_path: str) -> bytes:
        client = self._get_client()
        if client:
            res = client.get_object(Bucket=self.bucket_name, Key=storage_path)
            return res["Body"].read()
        return b"%PDF-1.4 simulated s3 content"

    def get_local_path(self, storage_path: str) -> Optional[Path]:
        return None

    def delete_file(self, storage_path: str) -> bool:
        client = self._get_client()
        if client:
            try:
                client.delete_object(Bucket=self.bucket_name, Key=storage_path)
                return True
            except Exception as e:
                logger.error(f"Failed to delete S3 object {storage_path}: {e}")
                return False
        return True

    def generate_download_url(self, storage_path: str, doc_id: str, expiry_seconds: int = 3600) -> str:
        client = self._get_client()
        if client:
            try:
                url = client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": storage_path},
                    ExpiresIn=expiry_seconds
                )
                return url
            except Exception as e:
                logger.error(f"Error generating S3 presigned URL: {e}")
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{storage_path}"


def get_storage_provider() -> BaseStorageProvider:
    """Factory selecting storage provider based on configuration."""
    if settings.STORAGE_BACKEND.lower() == "s3":
        return S3StorageProvider()
    return LocalStorageProvider()
