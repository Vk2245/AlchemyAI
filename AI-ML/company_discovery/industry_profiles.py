"""
Industry profile definitions.

Each profile defines the expected attributes, required fields, validation
hints, and taxonomy preferences for a specific industry. The system ships
with two demo profiles (electrical, software) but the architecture supports
any number of profiles -- add a new dict to PROFILES for any industry.

Profiles are plain dicts, not classes, so they can be serialized to JSON,
generated dynamically by an LLM, or loaded from a config file.
"""

from typing import Any


# ---------------------------------------------------------------------------
# Electrical industry profile
# ---------------------------------------------------------------------------

ELECTRICAL_PROFILE: dict[str, Any] = {
    "industry": "electrical",
    "display_name": "Electrical / Electronics",
    "description": "Power equipment, wiring, connectors, relays, lighting, electronic components",

    "required_attributes": [
        "Voltage Rating",
        "Current Rating",
        "Power Rating",
    ],

    "expected_attributes": [
        "Voltage Rating", "Current Rating", "Power Rating",
        "Frequency", "IP Rating", "Temperature Range",
        "Insulation Class", "Contact Material",
        "Certification", "Compliance Standard",
        "Dimensions", "Weight", "Mounting Type",
        "Number of Poles", "Breaking Capacity",
    ],

    "expected_units": {
        "Voltage Rating": ["V", "kV", "mV"],
        "Current Rating": ["A", "mA", "kA"],
        "Power Rating": ["W", "kW", "MW", "VA", "kVA"],
        "Frequency": ["Hz", "kHz", "MHz"],
        "Temperature Range": ["C", "F", "K"],
        "Weight": ["g", "kg", "lb", "oz"],
    },

    "validation_hints": {
        "voltage_range": {"min": 0, "max": 1000000},
        "current_range": {"min": 0, "max": 100000},
        "ip_rating_pattern": r"^IP\d{2}[A-Z]?$",
    },

    "taxonomy_hint": "Power Generation and Distribution, Electronic Components, Electrical Equipment",
    "typical_certifications": ["UL", "CE", "IEC", "CSA", "RoHS", "REACH"],
}


# ---------------------------------------------------------------------------
# Software / IT profile
# ---------------------------------------------------------------------------

SOFTWARE_PROFILE: dict[str, Any] = {
    "industry": "software",
    "display_name": "Software / IT",
    "description": "Application software, cloud services, IT infrastructure, development tools",

    "required_attributes": [
        "Version",
        "License Type",
    ],

    "expected_attributes": [
        "Version", "License Type", "Release Date",
        "End of Life Date", "End of Support Date",
        "Supported Platforms", "System Requirements",
        "API Availability", "Authentication Method",
        "Data Format", "Integration Protocols",
        "Pricing Model", "Deployment Type",
        "Security Certifications", "Compliance",
        "Language Support", "Max Users",
    ],

    "expected_units": {},

    "validation_hints": {
        "version_pattern": r"^\d+(\.\d+)*",
        "license_types": ["MIT", "Apache-2.0", "GPL", "BSD", "Proprietary", "AGPL",
                          "LGPL", "Commercial", "Freemium", "Open Source", "SaaS"],
    },

    "taxonomy_hint": "Information Technology, Software, Cloud Services",
    "typical_certifications": ["SOC2", "ISO 27001", "GDPR", "HIPAA", "FedRAMP", "PCI-DSS"],
}


# ---------------------------------------------------------------------------
# Generic fallback profile (works for any unrecognized industry)
# ---------------------------------------------------------------------------

GENERIC_PROFILE: dict[str, Any] = {
    "industry": "general",
    "display_name": "General / Other",
    "description": "Generic profile for any industry not specifically configured",

    "required_attributes": [],

    "expected_attributes": [
        "Dimensions", "Weight", "Material",
        "Certification", "Compliance",
        "Price", "Availability",
    ],

    "expected_units": {
        "Weight": ["g", "kg", "lb", "oz"],
    },

    "validation_hints": {},
    "taxonomy_hint": "General",
    "typical_certifications": [],
}


# ---------------------------------------------------------------------------
# Profile registry
# ---------------------------------------------------------------------------

PROFILES: dict[str, dict[str, Any]] = {
    "electrical": ELECTRICAL_PROFILE,
    "software": SOFTWARE_PROFILE,
    "general": GENERIC_PROFILE,
}


def get_profile(industry: str) -> dict[str, Any]:
    """
    Look up the industry profile for a given industry key.

    Returns the matching profile, or the generic fallback if the industry
    is not recognized.
    """
    # Normalize the key
    key = industry.lower().strip()

    # Direct match
    if key in PROFILES:
        return PROFILES[key]

    # Partial match: check if the key is contained in any profile key
    for profile_key, profile in PROFILES.items():
        if key in profile_key or profile_key in key:
            return profile

    return GENERIC_PROFILE


def list_profiles() -> list[str]:
    """Return all registered profile keys."""
    return list(PROFILES.keys())


def register_profile(industry: str, profile: dict[str, Any]) -> None:
    """
    Register a new industry profile at runtime.

    This allows dynamic profile creation -- for example, when the LLM
    detects an industry that does not have a pre-built profile, Stage 2
    can generate one on the fly and register it here.
    """
    PROFILES[industry.lower().strip()] = profile


# ---------------------------------------------------------------------------
# CLI: list profiles or show a specific one
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Available industry profiles:")
        for key in list_profiles():
            profile = PROFILES[key]
            print(f"  {key}: {profile['display_name']}")
        print()
        print("Usage: python -m company_discovery.industry_profiles <industry_key>")
        sys.exit(0)

    industry = sys.argv[1]
    profile = get_profile(industry)

    print(f"Profile: {profile['display_name']}")
    print(f"Industry: {profile['industry']}")
    print(f"Description: {profile['description']}")
    print()
    print("Required attributes:")
    for attr in profile["required_attributes"]:
        print(f"  - {attr}")
    print()
    print("Expected attributes:")
    for attr in profile["expected_attributes"]:
        print(f"  - {attr}")
    print()
    print("Full profile JSON:")
    print(json.dumps(profile, indent=2))
