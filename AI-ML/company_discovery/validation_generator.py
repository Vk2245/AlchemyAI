"""
Dynamic validation rule generation from industry profiles.

Takes an industry profile and generates a list of validation rule dicts
that the validation module can run against extracted records. This is how
industry-specific validation rules are created without hardcoding.
"""

import sys
import json
from typing import Any

from company_discovery.industry_profiles import get_profile
from validation.rules import (
    required_field_rule,
    numeric_range_rule,
    regex_pattern_rule,
    unit_consistency_rule,
    attribute_present_rule,
    DEFAULT_RULES,
)


def generate_validation_rules(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Generate a complete set of validation rules from an industry profile.

    Starts with the default rules (product_name required, etc.) and adds
    industry-specific rules based on the profile's required attributes,
    expected units, and validation hints.
    """
    rules = list(DEFAULT_RULES)  # Copy default rules

    # Required attributes become attribute_present rules
    for attr_name in profile.get("required_attributes", []):
        rules.append(attribute_present_rule(attr_name, severity="error"))

    # Expected units become unit_consistency rules
    for attr_name, units in profile.get("expected_units", {}).items():
        rules.append(unit_consistency_rule(attr_name, units, severity="warning"))

    # Validation hints may contain numeric ranges and patterns
    hints = profile.get("validation_hints", {})

    for hint_key, hint_value in hints.items():
        if hint_key.endswith("_range") and isinstance(hint_value, dict):
            # Numeric range hint, e.g. "voltage_range": {"min": 0, "max": 1000000}
            attr_name = hint_key.replace("_range", "").replace("_", " ").title()
            rules.append(numeric_range_rule(
                attr_name,
                min_value=hint_value.get("min"),
                max_value=hint_value.get("max"),
                severity="warning",
            ))

        elif hint_key.endswith("_pattern") and isinstance(hint_value, str):
            # Regex pattern hint, e.g. "ip_rating_pattern": r"^IP\d{2}$"
            attr_name = hint_key.replace("_pattern", "").replace("_", " ").title()
            rules.append(regex_pattern_rule(
                attr_name,
                pattern=hint_value,
                description=f"{attr_name} does not match expected format",
                severity="warning",
            ))

    return rules


def generate_rules_for_industry(industry: str) -> list[dict[str, Any]]:
    """
    Convenience function: look up the profile and generate its validation rules.
    """
    profile = get_profile(industry)
    return generate_validation_rules(profile)


# ---------------------------------------------------------------------------
# CLI: generate validation rules for an industry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m company_discovery.validation_generator <industry_key>")
        print("   e.g.: python -m company_discovery.validation_generator electrical")
        sys.exit(1)

    industry = sys.argv[1]
    rules = generate_rules_for_industry(industry)

    print(f"Validation rules for: {industry}")
    print(f"Total rules: {len(rules)}")
    print()

    for rule in rules:
        print(f"  [{rule.get('severity', '?').upper()}] {rule['type']}: {rule['message']}")
    print()
    print("Full rules JSON:")
    print(json.dumps(rules, indent=2))
