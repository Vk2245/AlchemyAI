import re

with open('C:\\VK224\\Projects\\Alchemy AI\\Project\\UNI-HACK\\DEV\\backend\\app\\api\\process.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I need to replace the sync with async_session_factory() as bg_db: block for Excel processing.
# Let's locate the block.

old_block = '''                    # We save the results by the thresholded category
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
                        await bg_db.commit()'''

new_block = '''                    # We save the results as a SINGLE aggregate ProductRecord to obey the 1-to-1 schema
                    async with async_session_factory() as bg_db:
                        # Clear existing records first
                        bg_doc = await bg_db.get(Document, doc_id)
                        if bg_doc:
                            await bg_db.execute(delete(ProductRecord).where(ProductRecord.document_id == bg_doc.id))
                            await bg_db.execute(delete(Report).where(Report.document_id == bg_doc.id))
                            
                        # Create an aggregate summary of all categories
                        category_record = {
                            "categories": [{"name": k, "item_count": len(v), "sample_items": v[:3]} for k, v in final_grouped_data.items()],
                            "source_file": original_filename,
                            "total_items": sum(len(v) for v in final_grouped_data.values())
                        }
                        
                        report_input = {
                            "record": {
                                "product_name": f"Bulk Catalog Data ({len(final_grouped_data)} Categories)",
                                "manufacturer": "Multiple Brands",
                                "industry": "Multiple",
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
                            risk_flags=[{"severity": "medium", "rule_name": "Bulk Excel Upload", "explanation": report_input["risks"]["detected_risks"][0]}]
                        )
                        html_content = render_to_html(report_md, title="Intelligence Report: Bulk Upload")
                        
                        report_id = f"Excel_Bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        report_pdf_path = REPORTS_DIR / f"report_{report_id}.pdf"
                        html_path = REPORTS_DIR / f"report_{report_id}.html"
                        
                        render_to_pdf(html_content, str(report_pdf_path))
                        with open(html_path, "w", encoding="utf-8") as f:
                            f.write(html_content)
                            
                        # Save to ProductRecord
                        content_hash = compute_content_hash(category_record)
                        pr = ProductRecord(
                            document_id=doc_id,
                            product_name=f"Bulk Excel: {category_record['total_items']} items",
                            industry="Multiple",
                            category="Bulk Upload",
                            record_data={"categories": final_grouped_data, "excel_path": excel_path},
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
                                details=f"excel_bulk_upload_items={category_record['total_items']}",
                            ))
                        await bg_db.commit()'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('C:\\VK224\\Projects\\Alchemy AI\\Project\\UNI-HACK\\DEV\\backend\\app\\api\\process.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced!")
else:
    print("Could not find the block.")
