"""
Runs validation rules against a TrustedProductRecord.

Takes a record and a list of rules, checks each rule, and returns a
ValidationResult with pass/fail per field and overall status.
"""

import re
import sys
import json
from typing import Any

from extraction.schema_models import (
    TrustedProductRecord,
    ValidationResult,
    ValidationIssue,
)
from validation.rules import DEFAULT_RULES


def validate_record(
    record: TrustedProductRecord,
    rules: list[dict[str, Any]] | None = None,
) -> ValidationResult:
    """
    Run all validation rules against a product record.

    Returns a ValidationResult with the list of issues found.
    If no rules are provided, uses the default rule set.
    """
    if rules is None:
        rules = DEFAULT_RULES

    issues: list[ValidationIssue] = []

    for rule in rules:
        rule_type = rule.get("type", "")

        if rule_type == "required_field":
            issue = _check_required_field(record, rule)
        elif rule_type == "numeric_range":
            issue = _check_numeric_range(record, rule)
        elif rule_type == "regex_pattern":
            issue = _check_regex_pattern(record, rule)
        elif rule_type == "unit_consistency":
            issue = _check_unit_consistency(record, rule)
        elif rule_type == "attribute_present":
            issue = _check_attribute_present(record, rule)
        else:
            continue

        if issue is not None:
            issues.append(issue)

    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    passed = error_count == 0

    return ValidationResult(
        passed=passed,
        issues=issues,
        error_count=error_count,
        warning_count=warning_count,
    )


def apply_validation_to_record(
    record: TrustedProductRecord,
    rules: list[dict[str, Any]] | None = None,
) -> TrustedProductRecord:
    """
    Validate a record and update its validation fields in place.

    Sets validation_passed, validation_errors, and fields_for_review
    on the record based on the validation result.
    """
    result = validate_record(record, rules)

    record.validation_passed = result.passed
    record.validation_errors = [i.message for i in result.issues if i.severity == "error"]
    record.fields_for_review = list(set(
        i.field for i in result.issues if i.severity in ("error", "warning")
    ))

    return record


# ---------------------------------------------------------------------------
# Rule checkers
# ---------------------------------------------------------------------------

def _check_required_field(
    record: TrustedProductRecord,
    rule: dict[str, Any],
) -> ValidationIssue | None:
    """Check if a top-level field on the record is present and non-empty."""
    field = rule["field"]
    value = getattr(record, field, None)

    if value is None or (isinstance(value, str) and value.strip() == ""):
        return ValidationIssue(
            field=field,
            rule="required_field",
            message=rule["message"],
            severity=rule.get("severity", "error"),
        )
    return None


def _check_attribute_present(
    record: TrustedProductRecord,
    rule: dict[str, Any],
) -> ValidationIssue | None:
    """Check if a named attribute exists in the record's attribute list."""
    attr_name = rule["attribute"].lower()
    found = any(a.name.lower() == attr_name for a in record.attributes)

    if not found:
        return ValidationIssue(
            field=rule["attribute"],
            rule="attribute_present",
            message=rule["message"],
            severity=rule.get("severity", "warning"),
        )
    return None


def _check_numeric_range(
    record: TrustedProductRecord,
    rule: dict[str, Any],
) -> ValidationIssue | None:
    """Check if a numeric attribute falls within the specified range."""
    attr_name = rule["attribute"].lower()
    matching = [a for a in record.attributes if a.name.lower() == attr_name]

    if not matching:
        return None  # Attribute not present, handled by attribute_present rule

    attr = matching[0]
    if attr.numeric_value is None:
        return ValidationIssue(
            field=rule["attribute"],
            rule="numeric_range",
            message=f"Attribute '{rule['attribute']}' has no numeric value to validate",
            severity="info",
        )

    min_val = rule.get("min_value")
    max_val = rule.get("max_value")

    if min_val is not None and attr.numeric_value < min_val:
        return ValidationIssue(
            field=rule["attribute"],
            rule="numeric_range",
            message=f"{rule['attribute']} value {attr.numeric_value} is below minimum {min_val}",
            severity=rule.get("severity", "warning"),
        )

    if max_val is not None and attr.numeric_value > max_val:
        return ValidationIssue(
            field=rule["attribute"],
            rule="numeric_range",
            message=f"{rule['attribute']} value {attr.numeric_value} exceeds maximum {max_val}",
            severity=rule.get("severity", "warning"),
        )

    return None


def _check_regex_pattern(
    record: TrustedProductRecord,
    rule: dict[str, Any],
) -> ValidationIssue | None:
    """Check if an attribute value matches the expected regex pattern."""
    attr_name = rule["attribute"].lower()
    matching = [a for a in record.attributes if a.name.lower() == attr_name]

    if not matching:
        return None

    attr = matching[0]
    pattern = rule["pattern"]

    if not re.match(pattern, attr.value, re.IGNORECASE):
        return ValidationIssue(
            field=rule["attribute"],
            rule="regex_pattern",
            message=rule["message"],
            severity=rule.get("severity", "warning"),
        )

    return None


def _check_unit_consistency(
    record: TrustedProductRecord,
    rule: dict[str, Any],
) -> ValidationIssue | None:
    """Check if an attribute's unit is one of the expected units."""
    attr_name = rule["attribute"].lower()
    matching = [a for a in record.attributes if a.name.lower() == attr_name]

    if not matching:
        return None

    attr = matching[0]
    expected = [u.lower() for u in rule["expected_units"]]

    if attr.unit and attr.unit.lower() not in expected:
        return ValidationIssue(
            field=rule["attribute"],
            rule="unit_consistency",
            message=rule["message"],
            severity=rule.get("severity", "warning"),
        )

    return None


# ---------------------------------------------------------------------------
# CLI: validate a record from a JSON file
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m validation.validate_record <record_json>")
        print()
        print("Validates a TrustedProductRecord JSON file against default rules.")
        sys.exit(1)

    record_path = sys.argv[1]

    with open(record_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    record = TrustedProductRecord(**data)
    result = validate_record(record)

    print(f"Validation passed: {result.passed}")
    print(f"Errors: {result.error_count}")
    print(f"Warnings: {result.warning_count}")
    print()

    for issue in result.issues:
        print(f"  [{issue.severity.upper()}] {issue.field}: {issue.message}")
