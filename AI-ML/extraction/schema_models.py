"""
Pydantic models for document data throughout the pipeline.

These are the core data shapes. Every module reads or writes using
these models. The DocumentRecord is the central artifact that
all later stages (3-7) consume.
"""

from typing import Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    """A single extracted document entity with provenance."""

    entity_type: str = Field(description="Entity type, e.g. 'PERSON', 'ORG', 'DATE', 'MONEY', 'LAW'")
    value: str = Field(description="Extracted value as a string, e.g. 'John Doe', '$5,000'")
    unit: Optional[str] = Field(
        default=None, description="Unit if applicable, e.g. 'USD', 'kg'"
    )
    numeric_value: Optional[float] = Field(
        default=None, description="Parsed numeric value if the attribute is numeric"
    )
    source_text: Optional[str] = Field(
        default=None,
        description="Exact snippet from the source document where this value was found",
    )
    source_page: Optional[int] = Field(
        default=None, description="Page number where this value was found (1-indexed)"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score between 0 and 1",
    )
    human_verified: bool = Field(
        default=False, description="Whether this entity has been verified/edited by a human"
    )


class DocumentRecord(BaseModel):
    """
    The central document record produced by Stages 0-2.

    All later stages (3-7) read from this record. It holds the extracted
    entities, metadata, provenance, and quality scores.
    """

    # Identity
    document_title: str = Field(description="Document title or inferred name")
    primary_party: Optional[str] = Field(
        default=None, description="Primary organization, vendor, or individual"
    )
    secondary_party: Optional[str] = Field(
        default=None, description="Secondary organization or individual (e.g., client, buyer)"
    )
    document_date: Optional[str] = Field(
        default=None, description="Primary date of the document"
    )
    summary: Optional[str] = Field(
        default=None, description="Brief document summary or intent"
    )

    # Classification
    document_type: Optional[str] = Field(
        default=None,
        description="Detected document type, e.g. 'invoice', 'contract', 'receipt', 'letter'",
    )
    category: Optional[str] = Field(
        default=None, description="Document category from taxonomy mapping"
    )
    subcategory: Optional[str] = Field(
        default=None, description="Document subcategory"
    )

    # Entities
    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="List of extracted named entities with provenance",
    )
    
    # Financial/Contract Summaries (Optional depending on doc type)
    financial_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted financial totals, taxes, or payment terms"
    )
    key_dates: dict[str, str] = Field(
        default_factory=dict,
        description="Map of key date types to their values (e.g. 'due_date': '2024-01-01')"
    )

    # Quality & Human-in-the-Loop
    record_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall record confidence score based on entity confidences",
    )
    validation_passed: bool = Field(
        default=False, description="Whether the record passed all validation rules"
    )
    validation_errors: list[str] = Field(
        default_factory=list,
        description="List of validation error messages",
    )
    fields_for_review: list[str] = Field(
        default_factory=list,
        description="Entity types flagged for human review (low confidence or missing)",
    )
    human_verified: bool = Field(
        default=False, description="Whether the entire document record has been verified by a human"
    )
    verified_by: Optional[str] = Field(
        default=None, description="Username or ID of the human reviewer"
    )

    # Provenance
    source_file: Optional[str] = Field(
        default=None, description="Original source file name"
    )
    content_hash: Optional[str] = Field(
        default=None, description="Hash of the source content for deduplication"
    )
    extracted_at: Optional[str] = Field(
        default=None, description="ISO timestamp of when extraction happened"
    )

    # Dynamic schema extension
    dynamic_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional type-specific attributes added by dynamic schema",
    )


class ExtractionResult(BaseModel):
    """
    Raw extraction output from the LLM/NER pipeline before validation and scoring.
    """

    document_title: str = Field(description="Document title or inferred name")
    document_type: Optional[str] = Field(
        default=None, description="Document type, e.g. 'invoice', 'contract', 'receipt', 'financial statement'"
    )
    primary_party: Optional[str] = Field(
        default=None, description="Primary organization, vendor, or individual"
    )
    document_date: Optional[str] = Field(
        default=None, description="Primary date of the document"
    )
    summary: Optional[str] = Field(
        default=None, description="Brief document summary"
    )
    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="All extracted named entities",
    )
    financial_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted financial totals, taxes, or payment terms"
    )
    key_dates: dict[str, str] = Field(
        default_factory=dict,
        description="Map of key date types to their values (e.g. 'due_date': '2024-01-01')"
    )


class ValidationIssue(BaseModel):
    """A single validation issue found in a document record."""

    field: str = Field(description="The field or entity type with the issue")
    rule: str = Field(description="The validation rule that was violated")
    message: str = Field(description="Human-readable description of the issue")
    severity: str = Field(
        default="warning",
        description="Severity level: 'error', 'warning', or 'info'",
    )


class ValidationResult(BaseModel):
    """Result of running validation rules against a document record."""

    passed: bool = Field(description="Whether all critical rules passed")
    issues: list[ValidationIssue] = Field(
        default_factory=list, description="List of validation issues found"
    )
    error_count: int = Field(default=0, description="Number of error-level issues")
    warning_count: int = Field(default=0, description="Number of warning-level issues")


# ---------------------------------------------------------------------------
# CLI: print model schemas for inspection
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    print("=== ExtractedEntity Schema ===")
    print(json.dumps(ExtractedEntity.model_json_schema(), indent=2))
    print()
    print("=== DocumentRecord Schema ===")
    print(json.dumps(DocumentRecord.model_json_schema(), indent=2))
    print()
    print("=== ExtractionResult Schema ===")
    print(json.dumps(ExtractionResult.model_json_schema(), indent=2))
