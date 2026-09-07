"""
Risk Radar module for Document Intelligence.

Performs static checks and email validation to flag suspicious documents,
acting as a precursor to Agentic Web Research.
"""

from typing import Any
from email_validator import validate_email as validate_email_address, EmailNotValidError

from extraction.schema_models import DocumentRecord

# List of common generic/free email domains that shouldn't typically be used for B2B billing
SUSPICIOUS_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"}


def detect_risk(record: DocumentRecord) -> dict[str, Any]:
    """
    Evaluates the DocumentRecord for static risks.
    Returns a dictionary of risk signals.
    """
    risk_flags = []
    suspicious_emails = []
    missing_critical_info = False

    # 1. Missing Critical Info Check
    # If it's an invoice, it MUST have a primary party (vendor) and a total amount.
    if record.document_type and "invoice" in record.document_type.lower():
        has_money = any(e.entity_type == "MONEY" for e in record.entities)
        if not record.primary_party or not has_money:
            missing_critical_info = True
            risk_flags.append("Invoice is missing vendor name or total amount.")

    # 2. Extract and Validate Emails
    emails = [e.value for e in record.entities if e.entity_type == "EMAIL" or "@" in e.value]
    
    for email in emails:
        try:
            # Validate format and optionally check MX records
            valid = validate_email_address(email, check_deliverability=False)
            domain = valid.domain.lower()
            
            # Check against free domains
            if domain in SUSPICIOUS_DOMAINS and "invoice" in (record.document_type or "").lower():
                suspicious_emails.append(email)
                risk_flags.append(f"Suspicious email domain for B2B invoice: {domain}")
        except EmailNotValidError as e:
            risk_flags.append(f"Invalid email format found: {email} ({str(e)})")

    # 3. Overall Risk Level
    overall_risk = "low"
    if len(risk_flags) > 0:
        overall_risk = "medium"
    if missing_critical_info or len(suspicious_emails) > 0:
        overall_risk = "high"

    return {
        "overall_risk_level": overall_risk,
        "risk_flags": risk_flags,
        "suspicious_emails": suspicious_emails,
        "requires_agentic_research": bool(record.primary_party and overall_risk in ["medium", "high"])
    }
