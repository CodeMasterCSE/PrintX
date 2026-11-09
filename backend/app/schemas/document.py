from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    original_filename: str
    file_size_bytes: int
    page_count: int
    is_encrypted: bool
    is_color: bool


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    mime_type: str
    status: str
    sha256_checksum: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str

