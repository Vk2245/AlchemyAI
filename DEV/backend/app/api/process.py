"""
Process API: upload PDFs and stream pipeline progress via SSE.

The /api/process endpoint:
  1. Accepts a PDF upload
  2. Saves it to the database
  3. Runs the AI-ML pipeline
  4. Streams progress updates as Server-Sent Events
  5. Saves the result to the database with a tamper-proof hash
"""

import sys
import hashlib
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentRecord, Report, AuditLog, get_db, async_session_factory
from app.api.auth import get_current_user, User
from app.core.security import (
    compute_content_hash, generate_safe_filename, validate_file_upload,
)
from app.core.config import (
    UPLOAD_DIR, REPORTS_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB,
    AI_ML_DIR, DEFAULT_PROVIDER,
)


router = APIRouter(prefix="/api", tags=["process"])


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a product PDF for analysis.

    Returns the document ID. Use /api/process/{doc_id} to start
    processing and stream progress.
    """
    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate
    is_valid, error = validate_file_upload(
        file.filename or "unknown",
        file_size,
        ALLOWED_EXTENSIONS,
        MAX_UPLOAD_SIZE_MB,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Generate safe filename and save
    safe_name = generate_safe_filename(file.filename or "document.pdf")
    file_path = UPLOAD_DIR / safe_name
    file_path.write_bytes(content)

    # Compute file hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Save to database
    doc = Document(
        owner_id=user.id,
        original_filename=file.filename or "document.pdf",
        stored_filename=safe_name,
        file_size_bytes=file_size,
        file_hash=file_hash,
        status="uploaded",
    )
    db.add(doc)
    await db.flush()

    # Audit log
    db.add(AuditLog(
        user_id=user.id,
        action="upload_document",
        resource_type="document",
        resource_id=doc.id,
        ip_address=request.client.host if request.client else None,
        details=f"filename={file.filename}, size={file_size}",
    ))

    return {
        "document_id": doc.id,
        "filename": file.filename,
        "file_hash": file_hash,
        "status": "uploaded",
        "message": "Document uploaded successfully. Use /api/process/{id} to start analysis.",
    }


# ---------------------------------------------------------------------------
# Process + SSE streaming endpoint
# ---------------------------------------------------------------------------

@router.get("/process/{doc_id}")
async def process_document(
    doc_id: int,
    request: Request,
    mode: str = "online",
    user: User = Depends(get_current_user),
):
    """
    Process a document and stream progress via Server-Sent Events.

    Each SSE event is a JSON object with:
      - progress: 0-100 (or -1 for error)
      - message: human-readable status message
      - data: optional payload (final result at 100%)
    """
    # Use a manual session for the initial lookup so we can close it
    # BEFORE returning the StreamingResponse. This prevents the
    # "no active connection" and "database is locked" errors that
    # occur when FastAPI's get_db dependency auto-closes mid-stream.
    async with async_session_factory() as init_db:
        result = await init_db.execute(
            select(Document).where(Document.id == doc_id, Document.owner_id == user.id)
        )
        doc = result.scalar_one_or_none()

        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        if doc.status == "processing":
            # Just log a warning instead of raising 409, because React Strict Mode 
            # will hit this endpoint twice and the second one needs to succeed
            logger.warning(f"Document {doc_id} is already processing, but allowing connection for dev mode")

        # Update status and commit
        doc.status = "processing"
        await init_db.commit()

        # Capture what we need before session closes
        stored_filename = doc.stored_filename
        original_filename = doc.original_filename
        pdf_path = str(UPLOAD_DIR / stored_filename)
        user_id = user.id

    is_excel = stored_filename.endswith((".xlsx", ".csv"))

    # Session is now cleanly closed. Build the SSE stream.
    async def event_stream():
        print(f"\n--- SSE STREAM CONNECTED FOR DOC {doc_id} ---")
        """Generator that runs the pipeline and yields SSE events."""
        import sys
        import json
        import asyncio
        import anyio
        import logging
        from datetime import datetime, timezone
        from sqlalchemy import delete
        
        logger = logging.getLogger(__name__)

        # Add AI-ML to Python path
        if str(AI_ML_DIR) not in sys.path:
            sys.path.insert(0, str(AI_ML_DIR))

        try:
            loop = asyncio.get_running_loop()
            q = asyncio.Queue()

            def worker_thread(is_excel_mode):
                def log(msg):
                    loop.call_soon_threadsafe(q.put_nowait, {"progress": 1, "message": "DEBUG: " + msg, "is_excel": is_excel_mode})

                log("THREAD STARTED")
                try:
                    if is_excel_mode:
                        log("IMPORTING EXCEL PIPELINE")
                        from pipeline.unilog_enrichment import process_unilog_catalogue
                        log("INITIALIZING EXCEL GENERATOR")
                        gen = process_unilog_catalogue(pdf_path)
                    else:
                        log("IMPORTING PDF PIPELINE")
                        from pipeline.run import run_pipeline
                        log("INITIALIZING PDF GENERATOR")
                        provider_to_use = DEFAULT_PROVIDER
                        gen = run_pipeline(pdf_path, provider=provider_to_use, execution_mode=mode)
                    
                    log("STARTING GENERATOR LOOP")
                    for update in gen:
                        loop.call_soon_threadsafe(q.put_nowait, update)
                    
                    log("FINISHED GENERATOR")
                    loop.call_soon_threadsafe(q.put_nowait, None)
                except Exception as e:
                    loop.call_soon_threadsafe(q.put_nowait, {"error": str(e)})

            # Use a raw OS thread to guarantee immediate execution, bypassing asyncio's executor pool
            import threading
            t = threading.Thread(target=worker_thread, args=(is_excel,), daemon=True)
            t.start()

            # No padding needed, let the browser buffer normally or flush if configured properly
            while True:
                update = await q.get()
                if update is None:
                    break
                    
                if "error" in update:
                    raise Exception(update["error"])
                    
                progress = update.get("progress", 0)
                message = update.get("message", "")
                data = update.get("data")
                
                event_data = {
                    "progress": progress,
                    "message": message,
                    "is_excel": is_excel
                }

                if is_excel:
                    if progress == 100 and data:
                        raw_grouped = data.get("grouped_data", {})
                        excel_path = data.get("excel_path", "")
                        
                        yield f"data: {json.dumps(event_data)}\n\n"
                        yield f"data: {json.dumps({'progress': 97, 'message': 'Saving to database and generating PDF reports...', 'is_excel': True})}\n\n"
                        
                        # --- Smart Category Thresholding Logic ---
                        sorted_categories = sorted(raw_grouped.items(), key=lambda x: len(x[1]), reverse=True)
                        MAX_REPORTS = 5
                        final_grouped_data = {}
                        
                        if len(sorted_categories) > MAX_REPORTS:
                            for i in range(MAX_REPORTS - 1):
                                cat_name, items = sorted_categories[i]
                                final_grouped_data[cat_name] = items
                                
                            misc_items = []
                            for cat_name, items in sorted_categories[MAX_REPORTS - 1:]:
                                misc_items.extend(items)
                                
                            if misc_items:
                                final_grouped_data["Miscellaneous Categories"] = misc_items
                        else:
                            final_grouped_data = raw_grouped

                        # We save the results as a SINGLE aggregate DocumentRecord
                        from report.generate_report import generate_report_markdown
                        from onepager.render_output import render_to_html, render_to_pdf
                        
                        async with async_session_factory() as bg_db:
                            bg_doc = await bg_db.get(Document, doc_id)
                            if bg_doc:
                                await bg_db.execute(delete(DocumentRecord).where(DocumentRecord.document_id == bg_doc.id))
                                await bg_db.execute(delete(Report).where(Report.document_id == bg_doc.id))
                                
                            category_record = {
                                "categories": [{"name": k, "item_count": len(v), "sample_items": v[:3]} for k, v in final_grouped_data.items()],
                                "source_file": original_filename,
                                "total_items": sum(len(v) for v in final_grouped_data.values())
                            }
                            
                            report_input = {
                                "record": {
                                    "document_title": f"Bulk Catalog Data ({len(final_grouped_data)} Categories)",
                                    "primary_party": "Multiple Brands",
                                    "document_type": "Multiple",
                                    "category": "Bulk Upload",
                                    "record_confidence": 0.95,
                                    "validation_passed": True,
                                    "record_data": category_record
                                },
                                "risks": {
                                    "overall_risk_level": "medium",
                                    "detected_risks": ["Review manual items for compliance"]
                                },
                                "web_results": f"Bulk generated from Excel upload. Represents {category_record['total_items']} items."
                            }
                            
                            report_md = generate_report_markdown(
                                record=report_input["record"],
                                risk_flags=[{"severity": "medium", "rule_name": "Bulk Excel Upload", "explanation": report_input["risks"]["detected_risks"][0]}],
                                agent_log=report_input.get("agent_log", [])
                            )
                            html_content = render_to_html(report_md, title="Intelligence Report: Bulk Upload")
                            
                            report_id = f"Excel_Bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            report_pdf_path = REPORTS_DIR / f"report_{report_id}.pdf"
                            html_path = REPORTS_DIR / f"report_{report_id}.html"
                            
                            render_to_pdf(html_content, str(report_pdf_path))
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(html_content)
                                
                            content_hash = compute_content_hash(category_record)
                            
                            # Include stats from the pipeline for the frontend dashboard
                            enrichment_stats = data.get("stats", {})
                            
                            pr = DocumentRecord(
                                document_id=doc_id,
                                document_title=f"Bulk Excel: {category_record['total_items']} items",
                                document_type="Multiple",
                                category="Bulk Upload",
                                record_data={
                                    "categories": final_grouped_data,
                                    "excel_path": excel_path,
                                    "stats": enrichment_stats,
                                },
                                record_confidence=0.90,
                                risk_level="medium",
                                content_hash=content_hash,
                            )
                            bg_db.add(pr)
                            await bg_db.flush()
                            
                            rep = Report(
                                document_id=doc_id,
                                report_markdown=report_md,
                                report_html_path=str(html_path),
                                report_pdf_path=str(report_pdf_path),
                            )
                            bg_db.add(rep)
                            
                            bg_doc.status = "completed"
                            bg_doc.processed_at = datetime.now(timezone.utc)
                            
                            bg_db.add(AuditLog(
                                user_id=user_id,
                                action="process_completed",
                                resource_type="document",
                                resource_id=bg_doc.id,
                                details=f"excel_bulk_upload_items={category_record['total_items']}",
                            ))
                            await bg_db.commit()

                        event_data = {
                            "progress": 100,
                            "message": "Bulk processing complete!",
                            "status": "completed",
                            "is_excel": True,
                            "data": {"categories_processed": len(final_grouped_data)}
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                    else:
                        yield f"data: {json.dumps(event_data)}\n\n"
                
                else:
                    # PDF logic
                    if progress == 100 and data:
                        record_data = data.get("record", {})
                        record_data["risks_summary"] = data.get("risks", {})
                        record_data["agent_log"] = data.get("agent_log", [])
                        content_hash = compute_content_hash(record_data)

                        async with async_session_factory() as bg_db:
                            bg_doc = await bg_db.get(Document, doc_id)
                            if bg_doc:
                                await bg_db.execute(delete(DocumentRecord).where(DocumentRecord.document_id == bg_doc.id))
                                await bg_db.execute(delete(Report).where(Report.document_id == bg_doc.id))
                                
                                document_record = DocumentRecord(
                                    document_id=bg_doc.id,
                                    document_title=record_data.get("document_title", ""),
                                    primary_party=record_data.get("primary_party", ""),
                                    part_number=record_data.get("part_number", ""),
                                    document_type=record_data.get("document_type", ""),
                                    category=record_data.get("category", ""),
                                    record_data=record_data,
                                    record_confidence=record_data.get("record_confidence", 0.0),
                                    validation_passed=record_data.get("validation_passed", False),
                                    risk_level=data.get("risks", {}).get("overall_risk_level", "low"),
                                    content_hash=content_hash,
                                )
                                bg_db.add(document_record)

                                try:
                                    from report.generate_report import generate_report_markdown
                                    from onepager.render_output import render_to_html, render_to_pdf
                                    
                                    report_md = data.get("report_md")
                                    if not report_md:
                                        report_md = generate_report_markdown(
                                            record=record_data,
                                            risk_flags=data.get("risks", {}).get("detected_risks", []),
                                            agent_log=data.get("agent_log", [])
                                        )
                                    html_content = render_to_html(report_md, title=f"Intelligence Report: {record_data.get('document_title', 'Unknown')}")
                                    
                                    report_id = f"PDF_{bg_doc.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                    report_pdf_path = REPORTS_DIR / f"report_{report_id}.pdf"
                                    html_path = REPORTS_DIR / f"report_{report_id}.html"
                                    
                                    render_to_pdf(html_content, str(report_pdf_path))
                                    with open(html_path, "w", encoding="utf-8") as f:
                                        f.write(html_content)
                                    
                                    report = Report(
                                        document_id=bg_doc.id,
                                        report_html_path=str(html_path),
                                        report_pdf_path=str(report_pdf_path),
                                    )
                                    bg_db.add(report)
                                    report_paths = {"html": str(html_path), "pdf": str(report_pdf_path)}
                                except Exception as e:
                                    logger.error(f"Failed to generate PDF report: {e}")
                                    report_paths = {}

                                bg_doc.status = "completed"
                                bg_doc.processed_at = datetime.now(timezone.utc)

                                bg_db.add(AuditLog(
                                    user_id=user_id,
                                    action="process_completed",
                                    resource_type="document",
                                    resource_id=bg_doc.id,
                                    details=f"document={record_data.get('document_title', '')}",
                                ))
                                await bg_db.commit()

                        event_data["status"] = "completed"
                        event_data["data"] = {
                            "record": record_data,
                            "risks": data.get("risks", {}),
                            "content_hash": content_hash,
                            "report_paths": report_paths,
                            "processing_time_sec": data.get("processing_time_sec", 0),
                        }
                        
                    yield f"data: {json.dumps(event_data)}\n\n"

        except Exception as e:
            logger.error(f"Pipeline error caught in stream: {e}")
            error_event = {"progress": -1, "message": f"Pipeline error: {str(e)}"}
            async with async_session_factory() as bg_db:
                bg_doc = await bg_db.get(Document, doc_id)
                if bg_doc:
                    bg_doc.status = "failed"
                    await bg_db.commit()
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ---------------------------------------------------------------------------
# Verify tamper-proof hash
# ---------------------------------------------------------------------------

@router.get("/verify/{doc_id}")
async def verify_record_integrity(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify that a product record has not been tampered with.

    Re-computes the HMAC-SHA256 of the stored record data and
    compares it to the stored hash. If they match, the record
    is intact. If not, it has been tampered with.
    """
    result = await db.execute(
        select(DocumentRecord)
        .join(Document)
        .where(Document.id == doc_id, Document.owner_id == user.id)
    )
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="Document record not found")

    # Re-compute hash
    current_hash = compute_content_hash(record.record_data)
    is_intact = current_hash == record.content_hash

    return {
        "document_id": doc_id,
        "document_title": record.document_title,
        "stored_hash": record.content_hash,
        "computed_hash": current_hash,
        "is_intact": is_intact,
        "verdict": "INTACT — record has not been tampered with" if is_intact
                   else "TAMPERED — record data has been modified!",
    }
