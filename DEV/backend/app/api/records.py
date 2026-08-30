"""
Records API: CRUD for saved product records and reports.

Provides history of all analyzed products for the authenticated user.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import Document, ProductRecord, Report, get_db
from app.api.auth import get_current_user, User


router = APIRouter(prefix="/api/records", tags=["records"])


# ---------------------------------------------------------------------------
# List all records for the current user
# ---------------------------------------------------------------------------

@router.get("/")
async def list_records(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all completed product records for the current user."""
    result = await db.execute(
        select(Document)
        .where(
            Document.owner_id == user.id,
            Document.status == "completed"
        )
        .order_by(Document.uploaded_at.desc())
    )
    documents = result.scalars().all()

    records = []
    for doc in documents:
        # Fetch associated product record
        pr_result = await db.execute(
            select(ProductRecord).where(ProductRecord.document_id == doc.id)
        )
        pr = pr_result.scalars().first()

        records.append({
            "document_id": doc.id,
            "original_filename": doc.original_filename,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
            "product_name": pr.product_name if pr else None,
            "manufacturer": pr.manufacturer if pr else None,
            "industry": pr.industry if pr else None,
            "record_confidence": pr.record_confidence if pr else None,
            "risk_level": pr.risk_level if pr else None,
            "content_hash": pr.content_hash if pr else None,
        })

    return {"count": len(records), "records": records}


# ---------------------------------------------------------------------------
# Get a single record
# ---------------------------------------------------------------------------

@router.get("/{doc_id}")
async def get_record(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the full product record for a specific document."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.owner_id == user.id)
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    pr_result = await db.execute(
        select(ProductRecord).where(ProductRecord.document_id == doc_id)
    )
    pr = pr_result.scalars().first()

    report_result = await db.execute(
        select(Report).where(Report.document_id == doc_id)
    )
    report = report_result.scalars().first()

    return {
        "document": {
            "id": doc.id,
            "original_filename": doc.original_filename,
            "status": doc.status,
            "file_hash": doc.file_hash,
            "file_size_bytes": doc.file_size_bytes,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
        },
        "product_record": {
            "product_name": pr.product_name,
            "manufacturer": pr.manufacturer,
            "part_number": pr.part_number,
            "industry": pr.industry,
            "category": pr.category,
            "record_confidence": pr.record_confidence,
            "validation_passed": pr.validation_passed,
            "risk_level": pr.risk_level,
            "content_hash": pr.content_hash,
            "record_data": pr.record_data,
        } if pr else None,
        "report": {
            "html_path": report.report_html_path,
            "pdf_path": report.report_pdf_path,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        } if report else None,
    }


# ---------------------------------------------------------------------------
# Delete a record
# ---------------------------------------------------------------------------

@router.delete("/{doc_id}")
async def delete_record(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and all associated records."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.owner_id == user.id)
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.delete(doc)

    return {"message": f"Document {doc_id} and all associated records deleted."}

# ---------------------------------------------------------------------------
# REGENERATE ALL PDFs (Temporary)
# ---------------------------------------------------------------------------

@router.get("/admin/regenerate_all_pdfs")
async def regenerate_all_pdfs(db: AsyncSession = Depends(get_db)):
    from app.models.database import Report
    import sys
    from pathlib import Path

    AI_ML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "AI-ML"
    if str(AI_ML_DIR) not in sys.path:
        sys.path.insert(0, str(AI_ML_DIR))

    from onepager.render_output import render_to_html, render_to_pdf  # type: ignore
    import os
    from pathlib import Path
    
    result = await db.execute(select(Report))
    reports = result.scalars().all()
    
    updated = 0
    errors = []
    for r in reports:
        try:
            if r.report_markdown and r.report_pdf_path:
                html_content = render_to_html(r.report_markdown, title="Product Intelligence Report")
                # Force create parent dirs
                Path(r.report_pdf_path).parent.mkdir(parents=True, exist_ok=True)
                render_to_pdf(html_content, r.report_pdf_path)
                updated += 1
                if r.report_html_path:
                    with open(r.report_html_path, "w", encoding="utf-8") as f:
                        f.write(html_content)
        except Exception as e:
            errors.append(str(e))
    
    return {"message": f"Successfully regenerated {updated} PDF reports. Errors: {errors}"}


# ---------------------------------------------------------------------------
# Download PDF Report
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/pdf")
async def download_pdf_report(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the generated PDF report for a specific document."""
    import os
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.owner_id == user.id)
    )
    doc = result.scalar_one_or_none()
    
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
        
    report_result = await db.execute(
        select(Report).where(Report.document_id == doc_id)
    )
    report = report_result.scalars().first()
    
    if not report or not report.report_pdf_path or not os.path.exists(report.report_pdf_path):
        raise HTTPException(status_code=404, detail="PDF report not found or not generated yet")
        
    return FileResponse(
        path=report.report_pdf_path,
        filename=f"Report_{doc.original_filename}.pdf",
        media_type="application/pdf"
    )

# ---------------------------------------------------------------------------
# Download Enriched CSV Report
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/csv")
async def download_csv_report(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the generated Enriched CSV report for a specific bulk document."""
    import os
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.owner_id == user.id)
    )
    doc = result.scalar_one_or_none()
    
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
        
    pr_result = await db.execute(
        select(ProductRecord).where(ProductRecord.document_id == doc_id)
    )
    pr = pr_result.scalars().first()
    
    if not pr or not pr.record_data or "excel_path" not in pr.record_data:
        raise HTTPException(status_code=404, detail="CSV report not found for this document")
        
    csv_path = pr.record_data["excel_path"]
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="CSV file missing on server")
        
    return FileResponse(
        path=csv_path,
        filename=f"Enriched_{doc.original_filename}.csv",
        media_type="text/csv"
    )
