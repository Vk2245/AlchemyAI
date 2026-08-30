"""
TOON (Token-Optimised Object Notation) utilities.

Converts Python dicts/lists to TOON format before sending to LLMs,
reducing token usage by 30-60% compared to raw JSON. Data is handled
as normal Python objects everywhere else -- TOON is only used at the
moment of prompt construction.
"""

import json
from typing import Any

try:
    import toon
    # Verify the expected API actually exists
    if hasattr(toon, 'dumps') and hasattr(toon, 'loads'):
        _HAS_TOON = True
    else:
        _HAS_TOON = False
except ImportError:
    _HAS_TOON = False


def to_toon(data: Any) -> str:
    """
    Convert a Python object (dict, list, etc.) to TOON string.

    Falls back to compact JSON if the python-toon library is not installed.
    Wrap the result in a fenced code block in your prompt so the LLM can
    parse the structure cleanly.
    """
    if _HAS_TOON:
        return toon.dumps(data)
    # Fallback: compact JSON (no extra whitespace)
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def from_toon(toon_string: str) -> Any:
    """
    Parse a TOON string back into a Python object.

    Falls back to JSON parsing if python-toon is not installed.
    """
    if _HAS_TOON:
        return toon.loads(toon_string)
    return json.loads(toon_string)


def wrap_for_prompt(data: Any, label: str = "data") -> str:
    """
    Convert data to TOON and wrap it in a labeled fenced code block.

    This is the standard way to inject structured data into an LLM prompt.
    The label helps the model distinguish multiple data blocks.

    Example output:
        [data]
        ```toon
        {name,value}
        Voltage,240V
        Current,10A
        ```
    """
    toon_str = to_toon(data)
    return f"[{label}]\n```toon\n{toon_str}\n```"


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample = [
        {"name": "Voltage Rating", "value": "240V", "unit": "V"},
        {"name": "Current Rating", "value": "10A", "unit": "A"},
        {"name": "IP Rating", "value": "IP67", "unit": None},
    ]

    print("Original JSON:")
    json_str = json.dumps(sample, indent=2)
    print(json_str)
    print(f"JSON length: {len(json_str)} chars")
    print()

    print("TOON format:")
    toon_str = to_toon(sample)
    print(toon_str)
    print(f"TOON length: {len(toon_str)} chars")
    print()

    savings = (1 - len(toon_str) / len(json_str)) * 100
    print(f"Token savings estimate: {savings:.1f}%")
    print()

    print("Wrapped for prompt:")
    print(wrap_for_prompt(sample, "product_attributes"))
