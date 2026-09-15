import asyncio
from sqlalchemy import select
from app.models.database import Document, DocumentRecord, Report, async_session_factory

async def run():
    async with async_session_factory() as db:
        # Get the latest document
        res = await db.execute(select(Document).order_by(Document.id.desc()).limit(1))
        doc = res.scalar_one_or_none()
        print(f"Latest Doc ID: {doc.id}")
        
        pr_result = await db.execute(
            select(DocumentRecord).where(DocumentRecord.document_id == doc.id)
        )
        pr = pr_result.scalars().first()
        
        report_result = await db.execute(
            select(Report).where(Report.document_id == doc.id)
        )
        report = report_result.scalars().first()
        
        # Test serialization (which is what FastAPI does)
        import json
        try:
            data = {
                "document": {
                    "id": doc.id,
                    "original_filename": doc.original_filename,
                    "status": doc.status,
                    "file_hash": doc.file_hash,
                    "file_size_bytes": doc.file_size_bytes,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
                },
                "document_record": {
                    "document_title": pr.document_title,
                    "primary_party": pr.primary_party,
                    "part_number": pr.part_number,
                    "document_type": pr.document_type,
                    "category": pr.category,
                    "record_confidence": pr.record_confidence,
                    "human_verified": pr.human_verified,
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
            json_str = json.dumps(data)
            print("Serialization successful! Length:", len(json_str))
        except Exception as e:
            print("Serialization FAILED:", e)

if __name__ == "__main__":
    asyncio.run(run())
