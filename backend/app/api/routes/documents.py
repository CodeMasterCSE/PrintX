from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.schemas.common import MessageResponse
from app.services.document_service import DocumentService, DocumentValidationError
from app.services.auth_service import get_current_user
from app.storage.storage_provider import get_storage_provider

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    """
    Uploads a PDF document.
    Validates file signature, structure, page counts, and encryption.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    # Read binary content
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file stream."
        )

    try:
        document = DocumentService.save_document(
            db=db,
            file_bytes=content,
            original_filename=file.filename,
            user=user
        )
    except DocumentValidationError as ve:
        raise HTTPException(status_code=ve.status_code, detail=ve.message)

    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(document),
        message=f"Document successfully validated: {document.page_count} page(s) ready for printing."
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Retrieves document details and metadata."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/preview")
def get_document_preview(document_id: str, page: int = 1, db: Session = Depends(get_db)):
    """Returns a PNG preview thumbnail of the document's specified page."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    image_bytes = DocumentService.generate_preview(doc, page_number=page)
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db)):
    """Downloads binary document content for Windows Print Controller or client."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    storage_provider = get_storage_provider()
    file_bytes = storage_provider.get_file_bytes(doc.storage_path)
    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'}
    )


@router.delete("/{document_id}", response_model=MessageResponse)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    """Deletes an uploaded document and purges its stored file from disk."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    DocumentService.delete_document(db, doc)
    return MessageResponse(message="Document deleted successfully.")

