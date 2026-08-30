"""
Dynamic safety/compliance rule generation.

Instead of hardcoded rules per industry, this module asks the LLM to
generate the top safety and compliance rules for ANY detected industry.
This is fully industry-agnostic -- works for electrical, software, food,
pharma, agriculture, automotive, or any other domain.
"""

import sys
import json
from typing import Any

from pydantic import BaseModel, Field

from config.llm_client import get_structured_output
from config.toon_utils import wrap_for_prompt


class SafetyRule(BaseModel):
    """A single generated safety/compliance rule."""

    rule_id: str = Field(description="Short unique ID like 'risk_001'")
    name: str = Field(description="Human-readable rule name")
    severity: str = Field(description="'critical', 'high', or 'medium'")
    description: str = Field(
        description="Why this rule matters for safety or compliance"
    )
    required_attribute: str = Field(
        description="The attribute name that should be present on the product"
    )
    alternate_names: list[str] = Field(
        default_factory=list,
        description="Alternate names for the same attribute",
    )
    condition_keywords: list[str] = Field(
        default_factory=list,
        description="Only trigger if these keywords appear in the product context. Empty = always trigger.",
    )


class GeneratedRuleSet(BaseModel):
    """Structured output: a set of safety rules for an industry."""

    industry: str = Field(default="", description="The industry these rules apply to")
    rules: list[SafetyRule] = Field(
        description="List of 5-8 safety/compliance rules for this industry"
    )
    reasoning: str = Field(
        default="Not provided",
        description="Brief explanation of how the rules were selected"
    )


SYSTEM_PROMPT = """You are a product safety and regulatory compliance expert.
Given an industry and product context, generate the most critical safety and
compliance rules that every product in this industry MUST satisfy.

Each rule checks whether a specific attribute is present on the product record.
If the attribute is missing, it represents a real safety or compliance risk.

Rules should be:
- Specific to the industry (not generic boilerplate)
- Ordered by severity (critical first)
- Practically useful (missing this attribute could cause real harm or legal issues)
- Named with the actual attribute name as it would appear on a spec sheet

Generate 5-8 rules. Use severity levels:
- critical: Missing this could cause injury, death, or major legal liability
- high: Missing this could cause product failure, recall, or regulatory fine
- medium: Missing this could cause customer complaints or minor compliance gaps"""


# Cache generated rules to avoid re-generating for the same industry
_rule_cache: dict[str, list[dict[str, Any]]] = {}


def generate_rules_for_industry(
    industry: str,
    product_domain: str = "",
    product_name: str = "",
    provider: str = "local",
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """
    Dynamically generate safety/compliance rules for any industry.

    Uses the LLM to produce 5-8 rules specific to the detected industry.
    Results are cached per industry key to avoid redundant LLM calls.

    Returns a list of rule dicts compatible with detect_risk.py.
    """
    cache_key = f"{industry}|{product_domain}".lower().strip()

    if use_cache and cache_key in _rule_cache:
        return _rule_cache[cache_key]

    context = wrap_for_prompt(
        {
            "industry": industry,
            "product_domain": product_domain or "general",
            "product_name": product_name or "unspecified",
        },
        "context",
    )

    prompt = f"""Generate the top safety and compliance rules for products in this industry.

{context}

For each rule, specify:
- The attribute that MUST be present on the product
- Why it matters (real-world consequence of it being missing)
- Severity level (critical/high/medium)
- Any condition keywords (only trigger if the product context mentions these)

Generate 5-8 rules, ordered by severity."""

    try:
        result = get_structured_output(
            prompt=prompt,
            response_model=GeneratedRuleSet,
            system_prompt=SYSTEM_PROMPT,
            provider=provider,
        )
    except Exception as e:
        print(f"Failed to generate dynamic rules: {e}")
        return []

    # Convert to the dict format used by detect_risk.py
    rules = []
    for rule in result.rules:
        rules.append({
            "id": rule.rule_id,
            "name": rule.name,
            "severity": rule.severity,
            "description": rule.description,
            "check": "attribute_missing",
            "attribute": rule.required_attribute,
            "alternate_attributes": rule.alternate_names,
            "condition_keywords": rule.condition_keywords if rule.condition_keywords else None,
        })

    # Cache
    _rule_cache[cache_key] = rules

    return rules


def clear_cache() -> None:
    """Clear the rule cache (useful for testing)."""
    _rule_cache.clear()


# ---------------------------------------------------------------------------
# CLI: generate rules for any industry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m risk_radar.dynamic_rules <industry> [product_domain]")
        print()
        print("Examples:")
        print("  python -m risk_radar.dynamic_rules electrical 'power distribution'")
        print("  python -m risk_radar.dynamic_rules food 'packaged beverages'")
        print("  python -m risk_radar.dynamic_rules pharmaceutical 'injectable drugs'")
        print("  python -m risk_radar.dynamic_rules software 'cloud SaaS'")
        print("  python -m risk_radar.dynamic_rules agriculture 'fertilizers'")
        sys.exit(1)

    industry = sys.argv[1]
    domain = sys.argv[2] if len(sys.argv) > 2 else ""

    print(f"Generating safety rules for: {industry} / {domain or 'general'}")
    print()

    rules = generate_rules_for_industry(industry, product_domain=domain)

    for rule in rules:
        print(f"  [{rule['severity'].upper()}] {rule['name']}")
        print(f"    Checks for: {rule['attribute']}")
        print(f"    Why: {rule['description']}")
        if rule.get("condition_keywords"):
            print(f"    Only when: {', '.join(rule['condition_keywords'])}")
        print()

    print(f"Total rules generated: {len(rules)}")
