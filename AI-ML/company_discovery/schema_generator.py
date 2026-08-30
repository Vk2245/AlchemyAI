"""
Dynamic schema generation from industry profiles.

Takes an industry profile dict and generates additional extraction
instructions and field definitions that the extraction module uses
to ask the LLM for industry-specific attributes.
"""

import sys
import json
from typing import Any

from company_discovery.industry_profiles import get_profile, GENERIC_PROFILE


def generate_schema_config(profile: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a schema configuration from an industry profile.

    The schema config tells the extraction module which additional
    attributes to look for beyond the base schema. It also provides
    unit hints and expected value patterns.

    Returns a dict with:
      - extra_instructions: text to append to the extraction prompt
      - required_attributes: list of attribute names that must be present
      - expected_attributes: list of attribute names to look for
      - unit_hints: dict mapping attribute names to expected units
    """
    required = profile.get("required_attributes", [])
    expected = profile.get("expected_attributes", [])
    units = profile.get("expected_units", {})

    # Build human-readable extraction instructions
    instruction_parts = []

    if required:
        instruction_parts.append(
            f"The following attributes are REQUIRED for this {profile.get('display_name', '')} product. "
            f"Extract them if present in the document: {', '.join(required)}."
        )

    if expected:
        non_required = [a for a in expected if a not in required]
        if non_required:
            instruction_parts.append(
                f"Also look for these industry-specific attributes: {', '.join(non_required)}."
            )

    if units:
        unit_hints = []
        for attr_name, unit_list in units.items():
            unit_hints.append(f"{attr_name} (units: {', '.join(unit_list)})")
        instruction_parts.append(
            f"Expected units: {'; '.join(unit_hints)}."
        )

    certs = profile.get("typical_certifications", [])
    if certs:
        instruction_parts.append(
            f"Look for certifications such as: {', '.join(certs)}."
        )

    extra_instructions = "\n".join(instruction_parts)

    return {
        "industry": profile.get("industry", "general"),
        "extra_instructions": extra_instructions,
        "required_attributes": required,
        "expected_attributes": expected,
        "unit_hints": units,
    }


def generate_schema_for_industry(industry: str) -> dict[str, Any]:
    """
    Convenience function: look up the profile and generate its schema config.
    """
    profile = get_profile(industry)
    return generate_schema_config(profile)


# ---------------------------------------------------------------------------
# CLI: generate schema config for an industry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m company_discovery.schema_generator <industry_key>")
        print("   e.g.: python -m company_discovery.schema_generator electrical")
        sys.exit(1)

    industry = sys.argv[1]
    config = generate_schema_for_industry(industry)

    print(f"Schema config for: {config['industry']}")
    print()
    print("Extra extraction instructions:")
    print(config["extra_instructions"])
    print()
    print("Required attributes:", config["required_attributes"])
    print("Expected attributes:", config["expected_attributes"])
    print()
    print("Full config:")
    print(json.dumps(config, indent=2))
