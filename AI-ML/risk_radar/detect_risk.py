"""
Risk detection engine.

Checks a trusted product record against dynamically generated
industry-specific safety/compliance rules. No hardcoded rule sets --
rules are generated on-the-fly by the LLM based on the detected industry.
"""

import sys
import json
from typing import Any

from config.llm_client import get_completion
from risk_radar.dynamic_rules import generate_rules_for_industry


def detect_risks(
    record: dict[str, Any],
    industry: str | None = None,
    product_domain: str = "",
    provider: str = "local",
) -> list[dict[str, Any]]:
    """
    Check a trusted record against dynamically generated industry rules.

    Steps:
      1. Determine the industry from the record (or use the override).
      2. Ask the LLM to generate the top safety rules for that industry.
      3. Run each rule as a deterministic check against the record.
      4. For each triggered flag, generate a plain-language explanation.

    Returns a list of risk flags with rule details and explanations.
    """
    # Determine industry
    if industry is None:
        industry = (record.get("industry") or "general").lower()
    if not product_domain:
        product_domain = (record.get("category") or "").lower()

    product_name = record.get("product_name", "")

    # Dynamically generate rules for this industry
    rules = generate_rules_for_industry(
        industry=industry,
        product_domain=product_domain,
        product_name=product_name,
        provider=provider,
    )

    if not rules:
        return []

    # Collect attribute names for quick lookup
    attr_names = set()
    for attr in record.get("attributes", []):
        attr_names.add(attr.get("name", "").lower())

    # Check document text for condition keywords
    description = (record.get("description") or "").lower()
    context_text = f"{product_name.lower()} {description}"

    flags: list[dict[str, Any]] = []

    for rule in rules:
        if rule["check"] == "attribute_missing":
            triggered = _check_attribute_missing(rule, attr_names, context_text)
            if triggered:
                flags.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "missing_attribute": rule["attribute"],
                })

    # Generate plain-language explanations
    if flags:
        flags = _add_explanations(flags, record, provider)

    return flags


def _check_attribute_missing(
    rule: dict[str, Any],
    attr_names: set[str],
    context_text: str,
) -> bool:
    """
    Check if a required attribute is missing from the record.

    If the rule has condition_keywords, only trigger if at least one
    keyword appears in the product context.
    """
    primary = rule["attribute"].lower()
    alternates = [a.lower() for a in rule.get("alternate_attributes", [])]
    all_names = [primary] + alternates

    # Check if any version of the attribute exists
    found = any(name in attr_names for name in all_names)
    if found:
        return False

    # Check condition keywords (if specified, only flag when relevant)
    keywords = rule.get("condition_keywords")
    if keywords:
        keyword_found = any(kw.lower() in context_text for kw in keywords)
        if not keyword_found:
            return False

    return True


def _add_explanations(
    flags: list[dict[str, Any]],
    record: dict[str, Any],
    provider: str,
) -> list[dict[str, Any]]:
    """Add LLM-generated plain-language explanations to each flag."""
    product_name = record.get("product_name", "unknown product")
    industry = record.get("industry", "unknown")

    for flag in flags:
        prompt = (
            f"A {industry} product '{product_name}' is missing: {flag['missing_attribute']}.\n"
            f"Rule: {flag['rule_name']}\n"
            f"Issue: {flag['description']}\n"
            f"Severity: {flag['severity']}\n\n"
            f"Write a 2-3 sentence plain-language explanation of why this missing "
            f"attribute is a real safety or compliance risk. Be specific to the "
            f"industry. No jargon."
        )

        try:
            explanation = get_completion(prompt, provider=provider)
            flag["explanation"] = explanation
        except Exception:
            flag["explanation"] = flag["description"]

    return flags


def get_risk_summary(
    flags: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize risk flags by severity."""
    critical = [f for f in flags if f["severity"] == "critical"]
    high = [f for f in flags if f["severity"] == "high"]
    medium = [f for f in flags if f["severity"] == "medium"]

    overall_risk = "critical" if critical else ("high" if high else ("medium" if medium else "low"))

    return {
        "overall_risk_level": overall_risk,
        "total_flags": len(flags),
        "critical": len(critical),
        "high": len(high),
        "medium": len(medium),
        "flags": flags,
    }


# ---------------------------------------------------------------------------
# CLI: run risk detection on a record
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m risk_radar.detect_risk <record_json> [industry]")
        print()
        print("Examples:")
        print("  python -m risk_radar.detect_risk record.json")
        print("  python -m risk_radar.detect_risk record.json electrical")
        print("  python -m risk_radar.detect_risk record.json food")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        record = json.load(f)

    industry = sys.argv[2] if len(sys.argv) > 2 else None
    flags = detect_risks(record, industry=industry)
    summary = get_risk_summary(flags)

    print(f"Product: {record.get('product_name', '?')}")
    print(f"Industry: {industry or record.get('industry', '?')}")
    print(f"Overall Risk: {summary['overall_risk_level'].upper()}")
    print(f"Risk flags: {summary['total_flags']}")
    print(f"  Critical: {summary['critical']}")
    print(f"  High: {summary['high']}")
    print(f"  Medium: {summary['medium']}")
    print()

    for flag in flags:
        print(f"  [{flag['severity'].upper()}] {flag['rule_name']}")
        print(f"    Missing: {flag['missing_attribute']}")
        print(f"    {flag.get('explanation', flag['description'])}")
        print()
