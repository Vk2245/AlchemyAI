"""
Pydantic models for product data throughout the pipeline.

These are the core data shapes. Every module reads or writes using
these models. The TrustedProductRecord is the central artifact that
all later stages (3-7) consume.
"""

from typing import Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class ProductAttribute(BaseModel):
    """A single extracted product attribute with provenance."""

    name: str = Field(description="Attribute name, e.g. 'Voltage Rating'")
    value: str = Field(description="Extracted value as a string, e.g. '240V'")
    unit: Optional[str] = Field(
        default=None, description="Unit if applicable, e.g. 'V', 'A', 'mm'"
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


class TrustedProductRecord(BaseModel):
    """
    The central product record produced by Stages 0-2.

    All later stages (3-7) read from this record. It holds the extracted
    attributes, metadata, provenance, and quality scores.
    """

    # Identity
    product_name: str = Field(description="Product name or title")
    manufacturer: Optional[str] = Field(
        default=None, description="Manufacturer or brand name"
    )
    part_number: Optional[str] = Field(
        default=None, description="Part number, model number, or SKU"
    )
    description: Optional[str] = Field(
        default=None, description="Short product description or summary"
    )

    # Classification
    industry: Optional[str] = Field(
        default=None,
        description="Detected industry, e.g. 'electrical', 'software', 'food'",
    )
    category: Optional[str] = Field(
        default=None, description="Product category from taxonomy mapping"
    )
    subcategory: Optional[str] = Field(
        default=None, description="Product subcategory"
    )

    # Attributes
    attributes: list[ProductAttribute] = Field(
        default_factory=list,
        description="List of extracted product attributes with provenance",
    )

    # Quality
    record_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall record confidence score",
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
        description="Attribute names flagged for human review (low confidence)",
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

    # Dynamic schema extension (set by Stage 2)
    industry_profile: Optional[str] = Field(
        default=None, description="Industry profile key used for this record"
    )
    dynamic_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional industry-specific attributes added by dynamic schema",
    )


class ExtractionResult(BaseModel):
    """
    Raw extraction output from the LLM before validation and scoring.

    This is what instructor returns. It gets converted into a
    TrustedProductRecord after validation and confidence scoring.
    """

    product_name: str = Field(description="Product name or title")
    manufacturer: Optional[str] = Field(
        default=None, description="Manufacturer or brand"
    )
    part_number: Optional[str] = Field(
        default=None, description="Part number or model number"
    )
    description: Optional[str] = Field(
        default=None, description="Brief product description"
    )
    attributes: list[ProductAttribute] = Field(
        default_factory=list,
        description="All extracted technical attributes",
    )


class ValidationIssue(BaseModel):
    """A single validation issue found in a product record."""

    field: str = Field(description="The field or attribute name with the issue")
    rule: str = Field(description="The validation rule that was violated")
    message: str = Field(description="Human-readable description of the issue")
    severity: str = Field(
        default="warning",
        description="Severity level: 'error', 'warning', or 'info'",
    )


class ValidationResult(BaseModel):
    """Result of running validation rules against a product record."""

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

    print("=== ProductAttribute Schema ===")
    print(json.dumps(ProductAttribute.model_json_schema(), indent=2))
    print()
    print("=== TrustedProductRecord Schema ===")
    print(json.dumps(TrustedProductRecord.model_json_schema(), indent=2))
    print()
    print("=== ExtractionResult Schema ===")
    print(json.dumps(ExtractionResult.model_json_schema(), indent=2))
