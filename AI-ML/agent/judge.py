"""
LLM-as-Judge for evaluating scraped content quality.

At each tier of the research pipeline, the judge evaluates whether
the scraped content is good enough to extract the missing attributes.
If it passes the threshold, we proceed. If not, we escalate to the
next tier.
"""

import sys
import json
from typing import Any

from pydantic import BaseModel, Field

from config.llm_client import get_structured_output


class JudgeVerdict(BaseModel):
    """Structured output from the LLM judge."""

    score: float = Field(
        ge=0.0, le=1.0,
        description="Quality score from 0.0 (useless) to 1.0 (perfect)",
    )
    passed: bool = Field(
        description="Whether the content is good enough to extract the missing attributes",
    )
    found_attributes: list[str] = Field(
        default_factory=list,
        description="Which of the missing attributes appear to be present in the content",
    )
    missing_still: list[str] = Field(
        default_factory=list,
        description="Which missing attributes are still not found in this content",
    )
    reasoning: str = Field(
        default="Not provided",
        description="Brief explanation of the quality assessment",
    )


# Default threshold: content must score above this to pass
QUALITY_THRESHOLD: float = 0.6


SYSTEM_PROMPT = """You are a quality judge for scraped product data. Given:
1. A product name and context
2. A list of missing attributes we're looking for
3. Scraped web content

Evaluate whether the scraped content contains enough information to
extract the missing attributes. Be strict but fair.

Scoring guide:
- 1.0: Content has clear, specific values for ALL missing attributes
- 0.8: Content has most attributes with good specificity
- 0.6: Content has at least half the attributes (threshold to pass)
- 0.4: Content has some info but vague or incomplete
- 0.2: Content is tangentially related but mostly useless
- 0.0: Content is completely irrelevant or empty"""


from config.settings import DEFAULT_PROVIDER

def judge_content(
    content: str,
    product_name: str,
    missing_attributes: list[str],
    threshold: float = QUALITY_THRESHOLD,
    provider: str = DEFAULT_PROVIDER,
) -> JudgeVerdict:
    """
    Evaluate whether scraped content is good enough to extract
    the missing attributes for a product.

    Returns a JudgeVerdict with score, pass/fail, and which
    attributes were found vs still missing.
    """
    # Trim content to avoid token bloat
    trimmed = content[:5000] if content else "(empty content)"

    attrs_str = ", ".join(missing_attributes) if missing_attributes else "general product specifications"

    prompt = f"""Evaluate this scraped web content for extracting product specifications.

Product: {product_name}
Missing attributes we need: {attrs_str}

Scraped content:
---
{trimmed}
---

Score the content quality and identify which missing attributes are present.
Set passed=true ONLY if the score is >= {threshold}."""

    verdict = get_structured_output(
        prompt=prompt,
        response_model=JudgeVerdict,
        system_prompt=SYSTEM_PROMPT,
        provider=provider,
    )

    # Enforce threshold
    verdict.passed = verdict.score >= threshold

    return verdict


def quick_relevance_check(
    content: str,
    product_name: str,
) -> bool:
    """
    Fast heuristic check: does the content even mention the product?

    This is a cheap pre-filter before the full LLM judge call.
    Returns True if the content appears relevant.
    """
    if not content or len(content.strip()) < 50:
        return False

    content_lower = content.lower()
    name_lower = product_name.lower()

    # Check if product name or significant parts appear in content
    name_parts = name_lower.split()
    matches = sum(1 for part in name_parts if part in content_lower and len(part) > 2)

    return matches >= max(1, len(name_parts) // 2)


# ----------------------------------------------------------------
# CLI: test the judge
# ----------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python -m agent.judge <content_file_or_text> <product_name> <missing_attr1,missing_attr2,...>")
        print()
        print("Examples:")
        print("  python -m agent.judge scraped.txt 'ABB SACE Tmax' 'IP Rating,Voltage Rating'")
        print("  python -m agent.judge 'This relay has IP67 rating and 24V DC coil' 'Omron G2R' 'IP Rating,Voltage'")
        sys.exit(1)

    content_arg = sys.argv[1]
    product_name = sys.argv[2]
    missing = sys.argv[3].split(",")

    # Check if first arg is a file path or inline text
    from pathlib import Path
    if Path(content_arg).exists():
        with open(content_arg, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = content_arg

    print(f"Judging content for: {product_name}")
    print(f"Missing attributes: {missing}")
    print(f"Content length: {len(content)} chars")
    print()

    # Quick relevance check
    relevant = quick_relevance_check(content, product_name)
    print(f"Quick relevance check: {'RELEVANT' if relevant else 'NOT RELEVANT'}")

    if not relevant:
        print("Content does not appear relevant. Skipping full judge.")
        sys.exit(0)

    # Full LLM judge
    verdict = judge_content(content, product_name, missing)

    print(f"\nJudge Verdict:")
    print(f"  Score: {verdict.score:.2f}")
    print(f"  Passed: {verdict.passed}")
    print(f"  Found: {verdict.found_attributes}")
    print(f"  Still missing: {verdict.missing_still}")
    print(f"  Reasoning: {verdict.reasoning}")
