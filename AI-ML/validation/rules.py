"""
Validation rule definitions.

Rules are plain dicts describing checks to run against product records.
This keeps them serializable and easy to generate dynamically from
industry profiles in Stage 2.
"""

import re
from typing import Any


# ---------------------------------------------------------------------------
# Rule types
# ---------------------------------------------------------------------------

def required_field_rule(field_name: str, severity: str = "error") -> dict[str, Any]:
    """
    Create a rule that checks whether a field or attribute is present and non-empty.
    """
    return {
        "type": "required_field",
        "field": field_name,
        "severity": severity,
        "message": f"Required field '{field_name}' is missing or empty",
    }


def numeric_range_rule(
    attribute_name: str,
    min_value: float | None = None,
    max_value: float | None = None,
    severity: str = "warning",
) -> dict[str, Any]:
    """
    Create a rule that checks if a numeric attribute falls within a range.
    """
    range_desc = ""
    if min_value is not None and max_value is not None:
        range_desc = f"between {min_value} and {max_value}"
    elif min_value is not None:
        range_desc = f"at least {min_value}"
    elif max_value is not None:
        range_desc = f"at most {max_value}"

    return {
        "type": "numeric_range",
        "attribute": attribute_name,
        "min_value": min_value,
        "max_value": max_value,
        "severity": severity,
        "message": f"Attribute '{attribute_name}' should be {range_desc}",
    }


def regex_pattern_rule(
    attribute_name: str,
    pattern: str,
    description: str = "",
    severity: str = "warning",
) -> dict[str, Any]:
    """
    Create a rule that checks if an attribute value matches a regex pattern.
    """
    return {
        "type": "regex_pattern",
        "attribute": attribute_name,
        "pattern": pattern,
        "severity": severity,
        "message": description or f"Attribute '{attribute_name}' does not match expected pattern",
    }


def unit_consistency_rule(
    attribute_name: str,
    expected_units: list[str],
    severity: str = "warning",
) -> dict[str, Any]:
    """
    Create a rule that checks if an attribute's unit is one of the expected units.
    """
    return {
        "type": "unit_consistency",
        "attribute": attribute_name,
        "expected_units": expected_units,
        "severity": severity,
        "message": (
            f"Attribute '{attribute_name}' has unexpected unit. "
            f"Expected one of: {', '.join(expected_units)}"
        ),
    }


def attribute_present_rule(
    attribute_name: str,
    severity: str = "warning",
) -> dict[str, Any]:
    """
    Create a rule that checks whether a specific attribute exists in the record.
    """
    return {
        "type": "attribute_present",
        "attribute": attribute_name,
        "severity": severity,
        "message": f"Expected attribute '{attribute_name}' is not present",
    }


# ---------------------------------------------------------------------------
# Default rules (industry-agnostic, apply to all records)
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[dict[str, Any]] = [
    required_field_rule("product_name", severity="error"),
    required_field_rule("description", severity="warning"),
]


# ---------------------------------------------------------------------------
# CLI: print all default rules
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    print("=== Default Validation Rules ===")
    print(json.dumps(DEFAULT_RULES, indent=2))
    print(f"\nTotal rules: {len(DEFAULT_RULES)}")
