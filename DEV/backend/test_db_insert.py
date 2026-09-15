import asyncio
from sqlalchemy import select
from app.models.database import DocumentRecord, async_session_factory

async def run():
    try:
        async with async_session_factory() as db:
            final_grouped_data = {
                "Pipes": [{"Item_ID": "PROD_0001"}],
                None: [{"Item_ID": "PROD_0002"}]
            }
            pr = DocumentRecord(
                document_id=72,
                document_title="Test",
                document_type="Test",
                category="Test",
                record_data={
                    "categories": final_grouped_data,
                    "excel_path": "path",
                    "stats": {}
                },
                record_confidence=0.90,
                risk_level="medium",
                content_hash="hash"
            )
            db.add(pr)
            await db.flush()
            print("Database Insert OK!")
            await db.rollback()
    except Exception as e:
        print("CRASH:", type(e), e)

if __name__ == "__main__":
    asyncio.run(run())
