"""
Human-in-the-Loop Review API.

Allows users to fetch, edit, and verify extracted entities for a document.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import json

from app.models.database import Document, DocumentRecord, AuditLog, get_db
from app.api.auth import get_current_user, User
from app.core.security import compute_content_hash

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("/{doc_id}/verify")
async def verify_document_record(
    doc_id: int,
    verified_data: dict = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save the human-verified record data and mark it as verified.
    
    Expected body:
    {
        "record_data": {
            "entities": [...],
            "document_title": "...",
            ...
        }
    }
    """
    # Verify ownership
    doc_result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.owner_id == user.id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Fetch the record
    record_result = await db.execute(
        select(DocumentRecord).where(DocumentRecord.document_id == doc_id)
    )
    record = record_result.scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Document record not found")

    # Extract verified payload
    new_record_data = verified_data.get("record_data")
    if not new_record_data:
        raise HTTPException(status_code=400, detail="Missing record_data in request body")

    # Update top-level fields for fast querying
    record.document_title = new_record_data.get("document_title", record.document_title)
    record.primary_party = new_record_data.get("primary_party", record.primary_party)
    record.document_type = new_record_data.get("document_type", record.document_type)
    
    # All verified documents get a 100% confidence score essentially, 
    # but we can preserve the AI confidence and just set the verified flag.
    record.human_verified = True
    record.verified_by = user.id
    record.verified_at = datetime.now(timezone.utc)
    
    # Save the updated raw JSON
    record.record_data = new_record_data
    
    # Recompute tamper-proof hash with human edits included
    record.content_hash = compute_content_hash(new_record_data)

    # Log the action
    db.add(AuditLog(
        user_id=user.id,
        action="human_verification",
        resource_type="document_record",
        resource_id=record.id,
        details=f"doc_id={doc_id}"
    ))

    await db.commit()

    return {
        "message": "Document record successfully verified and updated",
        "document_id": doc_id,
        "content_hash": record.content_hash
    }
