import re

with open('C:\\VK224\\Projects\\Alchemy AI\\Project\\UNI-HACK\\DEV\\backend\\app\\api\\process.py', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "# ---------------------------------------------------------------------------\n# Process + SSE streaming endpoint"
end_marker = "# ---------------------------------------------------------------------------\n# Verify tamper-proof hash"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Markers not found!")
    exit(1)

new_content = '''# ---------------------------------------------------------------------------
# Process + SSE streaming endpoint
# ---------------------------------------------------------------------------

@router.get("/process/{doc_id}")
async def process_document(
    doc_id: int,
    request: Request,
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
            raise HTTPException(status_code=409, detail="Document is already being processed")

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
        """Generator that runs the pipeline and yields SSE events."""
        # Add AI-ML to Python path
        if str(AI_ML_DIR) not in sys.path:
            sys.path.insert(0, str(AI_ML_DIR))

        try:
            if is_excel:
                from pipeline.unilog_enrichment import process_unilog_catalogue
                from report.generate_report import generate_report_markdown
                from onepager.render_output import render_to_html, render_to_pdf
                import uuid
                
                # Stream progress from the generator
                final_data = None
                for update in process_unilog_catalogue(pdf_path):
                    progress = update.get("progress", 0)
                    message = update.get("message", "")
                    data = update.get("data")
                    
                    if progress == 100 and data:
                        final_data = data
                    
                    event_data = {"progress": progress, "message": message}
                    yield f"data: {json.dumps(event_data)}\\n\\n"
                    
                    if progress == -1:
                        break
                        
                if final_data:
                    raw_grouped = final_data.get("grouped_data", {})
                    excel_path = final_data.get("excel_path", "")
                    
                    yield f"data: {json.dumps({'progress': 97, 'message': 'Saving to database and generating PDF reports...'})}\\n\\n"
                    
                    # --- Smart Category Thresholding Logic ---
                    # Sort categories by size (descending)
                    sorted_categories = sorted(raw_grouped.items(), key=lambda x: len(x[1]), reverse=True)
                    
                    # Limit to Top 5 categories. Everything else goes into "Miscellaneous"
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

                    # We save the results by the thresholded category
                    async with async_session_factory() as bg_db:
                        # Clear existing records first
                        bg_doc = await bg_db.get(Document, doc_id)
                        if bg_doc:
                            await bg_db.execute(delete(ProductRecord).where(ProductRecord.document_id == bg_doc.id))
                            await bg_db.execute(delete(Report).where(Report.document_id == bg_doc.id))
                            
                        for category, items in final_grouped_data.items():
                            # Create a summary product record for this category
                            category_record = {
                                "category_name": category,
                                "item_count": len(items),
                                "sample_items": items[:5],
                                "source_file": original_filename
                            }
                            
                            # Generate a PDF report for this category
                            report_input = {
                                "record": {
                                    "product_name": f"Bulk Upload: {category}",
                                    "manufacturer": "Multiple Brands",
                                    "industry": category,
                                    "category": category,
                                    "record_confidence": 0.95,
                                    "validation_passed": True,
                                    "record_data": category_record
                                },
                                "risks": {
                                    "overall_risk_level": "medium",
                                    "detected_risks": ["Review manual items for compliance"]
                                },
                                "web_results": f"Bulk generated from Excel upload. Represents {len(items)} items."
                            }
                            
                            report_md = generate_report_markdown(
                                record=report_input["record"],
                                risk_flags=[{"severity": "medium", "rule_name": "Bulk Excel Upload", "explanation": report_input["risks"]["detected_risks"][0]}]
                            )
                            html_content = render_to_html(report_md, title=f"Intelligence Report: {category}")
                            
                            report_id = f"Excel_{category.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            report_pdf_path = REPORTS_DIR / f"report_{report_id}.pdf"
                            html_path = REPORTS_DIR / f"report_{report_id}.html"
                            
                            render_to_pdf(html_content, str(report_pdf_path))
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(html_content)
                                
                            # Save to ProductRecord
                            content_hash = compute_content_hash(category_record)
                            pr = ProductRecord(
                                document_id=doc_id,
                                product_name=f"Bulk Category: {category}",
                                industry=category,
                                category=category,
                                record_data={"items": items, "excel_path": excel_path},
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
                        
                        if bg_doc:
                            bg_doc.status = "completed"
                            bg_doc.processed_at = datetime.now(timezone.utc)
                            bg_db.add(AuditLog(
                                user_id=user_id,
                                action="process_completed",
                                resource_type="document",
                                resource_id=bg_doc.id,
                                details=f"excel_bulk_upload_categories={len(final_grouped_data)}",
                            ))
                        await bg_db.commit()

                    event_data = {
                        "progress": 100,
                        "message": "Bulk processing complete!",
                        "status": "completed",
                        "data": {"categories_processed": len(final_grouped_data)}
                    }
                    yield f"data: {json.dumps(event_data)}\\n\\n"

            else:
                # PDF Pipeline
                from pipeline.run import run_pipeline

                for update in run_pipeline(pdf_path, provider=DEFAULT_PROVIDER):
                    progress = update.get("progress", 0)
                    message = update.get("message", "")
                    data = update.get("data")

                    event_data = {
                        "progress": progress,
                        "message": message,
                    }

                    if progress == 100 and data:
                        # Save results to database
                        record_data = data.get("record", {})
                        record_data["risks_summary"] = data.get("risks", {})
                        record_data["agent_log"] = data.get("agent_log", [])
                        content_hash = compute_content_hash(record_data)

                        async with async_session_factory() as bg_db:
                            bg_doc = await bg_db.get(Document, doc_id)
                            if bg_doc:
                                # Delete existing records to allow re-processing and prevent IntegrityError
                                await bg_db.execute(delete(ProductRecord).where(ProductRecord.document_id == bg_doc.id))
                                await bg_db.execute(delete(Report).where(Report.document_id == bg_doc.id))
                                
                                product_record = ProductRecord(
                                    document_id=bg_doc.id,
                                    product_name=record_data.get("product_name", ""),
                                    manufacturer=record_data.get("manufacturer", ""),
                                    part_number=record_data.get("part_number", ""),
                                    industry=record_data.get("industry", ""),
                                    category=record_data.get("category", ""),
                                    record_data=record_data,
                                    record_confidence=record_data.get("record_confidence", 0.0),
                                    validation_passed=record_data.get("validation_passed", False),
                                    risk_level=data.get("risks", {}).get("overall_risk_level", "low"),
                                    content_hash=content_hash,
                                )
                                bg_db.add(product_record)

                                # Save report
                                report_paths = data.get("report_paths", {})
                                report = Report(
                                    document_id=bg_doc.id,
                                    report_html_path=report_paths.get("html", ""),
                                    report_pdf_path=report_paths.get("pdf", ""),
                                )
                                bg_db.add(report)

                                bg_doc.status = "completed"
                                bg_doc.processed_at = datetime.now(timezone.utc)

                                # Audit
                                bg_db.add(AuditLog(
                                    user_id=user_id,
                                    action="process_completed",
                                    resource_type="document",
                                    resource_id=bg_doc.id,
                                    details=f"product={record_data.get('product_name', '')}",
                                ))
                                await bg_db.commit()

                        # Add content hash and complete status to SSE response
                        event_data["status"] = "completed"
                        event_data["data"] = {
                            "record": record_data,
                            "risks": data.get("risks", {}),
                            "content_hash": content_hash,
                            "report_paths": report_paths,
                            "processing_time_sec": data.get("processing_time_sec", 0),
                        }

                    elif progress == -1:
                        # Error
                        async with async_session_factory() as bg_db:
                            bg_doc = await bg_db.get(Document, doc_id)
                            if bg_doc:
                                bg_doc.status = "failed"
                                bg_db.add(AuditLog(
                                    user_id=user_id,
                                    action="process_failed",
                                    resource_type="document",
                                    resource_id=bg_doc.id,
                                    details=message,
                                ))
                                await bg_db.commit()

                    yield f"data: {json.dumps(event_data)}\\n\\n"

        except Exception as e:
            error_event = {"progress": -1, "message": f"Pipeline error: {str(e)}"}
            async with async_session_factory() as bg_db:
                bg_doc = await bg_db.get(Document, doc_id)
                if bg_doc:
                    bg_doc.status = "failed"
                    await bg_db.commit()
            yield f"data: {json.dumps(error_event)}\\n\\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

'''

with open('C:\\VK224\\Projects\\Alchemy AI\\Project\\UNI-HACK\\DEV\\backend\\app\\api\\process.py', 'w', encoding='utf-8') as f:
    f.write(content[:start_idx] + new_content + content[end_idx:])

print("Successfully replaced process logic.")
