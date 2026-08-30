"""
Product taxonomy categories.

Defines a flat list of product categories loosely based on UNSPSC
(United Nations Standard Products and Services Code). These are used
as few-shot context for the zero-shot taxonomy classifier.

The taxonomy is industry-agnostic -- it covers electrical, software,
mechanical, food, agriculture, pharmaceutical, and more. The classifier
picks the best match from this list.
"""

from typing import Any


# Each category has: code, segment, family, class, description
TAXONOMY: list[dict[str, str]] = [
    # Electrical / Electronics
    {"code": "26000000", "segment": "Power Generation and Distribution",
     "family": "Electrical Equipment", "class": "Power Distribution",
     "description": "Transformers, switchgear, circuit breakers, panels"},
    {"code": "26100000", "segment": "Power Generation and Distribution",
     "family": "Wiring and Cabling", "class": "Cables and Connectors",
     "description": "Power cables, data cables, connectors, terminals"},
    {"code": "26110000", "segment": "Power Generation and Distribution",
     "family": "Lighting", "class": "Lighting Equipment",
     "description": "Luminaires, lamps, LED fixtures, controls"},
    {"code": "32000000", "segment": "Electronic Components",
     "family": "Semiconductors", "class": "Active Components",
     "description": "ICs, transistors, diodes, microcontrollers"},
    {"code": "32100000", "segment": "Electronic Components",
     "family": "Passive Components", "class": "Passive Components",
     "description": "Resistors, capacitors, inductors, filters"},
    {"code": "39100000", "segment": "Electrical Equipment",
     "family": "Relays and Contactors", "class": "Switching Devices",
     "description": "Relays, contactors, motor starters, timers"},

    # Software / IT
    {"code": "43000000", "segment": "Information Technology",
     "family": "Software", "class": "Application Software",
     "description": "Enterprise software, productivity tools, CRM, ERP"},
    {"code": "43100000", "segment": "Information Technology",
     "family": "Infrastructure Software", "class": "System Software",
     "description": "Operating systems, middleware, databases, security"},
    {"code": "43110000", "segment": "Information Technology",
     "family": "Cloud Services", "class": "Cloud Computing",
     "description": "SaaS, PaaS, IaaS, cloud storage, serverless"},
    {"code": "43200000", "segment": "Information Technology",
     "family": "Hardware", "class": "Computer Hardware",
     "description": "Servers, workstations, storage, networking equipment"},
    {"code": "43210000", "segment": "Information Technology",
     "family": "Networking", "class": "Network Equipment",
     "description": "Routers, switches, firewalls, access points"},

    # Mechanical / Industrial
    {"code": "23000000", "segment": "Industrial Machinery",
     "family": "Manufacturing Equipment", "class": "Machine Tools",
     "description": "CNC machines, lathes, mills, presses"},
    {"code": "23100000", "segment": "Industrial Machinery",
     "family": "Material Handling", "class": "Conveyors and Lifts",
     "description": "Conveyors, hoists, cranes, forklifts"},
    {"code": "27000000", "segment": "Tools and Hardware",
     "family": "Hand Tools", "class": "General Hardware",
     "description": "Fasteners, brackets, hand tools, measuring"},
    {"code": "31000000", "segment": "Manufacturing Components",
     "family": "Bearings and Seals", "class": "Mechanical Components",
     "description": "Bearings, seals, gaskets, springs, gears"},
    {"code": "40000000", "segment": "HVAC and Plumbing",
     "family": "Heating and Cooling", "class": "HVAC Systems",
     "description": "HVAC units, compressors, pumps, valves, pipes"},

    # Food / Agriculture
    {"code": "50000000", "segment": "Food and Beverage",
     "family": "Processed Food", "class": "Food Products",
     "description": "Packaged food, beverages, ingredients, additives"},
    {"code": "50100000", "segment": "Food and Beverage",
     "family": "Fresh Produce", "class": "Agricultural Products",
     "description": "Fruits, vegetables, grains, dairy, meat"},
    {"code": "10000000", "segment": "Agriculture",
     "family": "Farming Equipment", "class": "Agricultural Machinery",
     "description": "Tractors, harvesters, irrigation, seeders"},
    {"code": "10100000", "segment": "Agriculture",
     "family": "Seeds and Fertilizers", "class": "Agricultural Inputs",
     "description": "Seeds, fertilizers, pesticides, feed"},

    # Pharmaceutical / Medical
    {"code": "42000000", "segment": "Medical Equipment",
     "family": "Diagnostic Equipment", "class": "Medical Devices",
     "description": "Imaging, lab instruments, monitors, diagnostic tools"},
    {"code": "42100000", "segment": "Medical Equipment",
     "family": "Surgical Equipment", "class": "Surgical Instruments",
     "description": "Surgical tools, implants, prosthetics"},
    {"code": "51000000", "segment": "Pharmaceuticals",
     "family": "Drug Products", "class": "Pharmaceutical Products",
     "description": "Prescription drugs, OTC medications, vaccines"},

    # Chemical / Materials
    {"code": "12000000", "segment": "Chemicals",
     "family": "Industrial Chemicals", "class": "Chemical Products",
     "description": "Solvents, adhesives, coatings, raw chemicals"},
    {"code": "13000000", "segment": "Materials",
     "family": "Raw Materials", "class": "Metals and Polymers",
     "description": "Steel, aluminum, plastics, composites, rubber"},

    # Safety / PPE
    {"code": "46000000", "segment": "Safety and Security",
     "family": "Personal Protective Equipment", "class": "Safety Gear",
     "description": "Helmets, gloves, goggles, fire extinguishers"},

    # General / Uncategorized
    {"code": "99000000", "segment": "General",
     "family": "Uncategorized", "class": "Other Products",
     "description": "Products that do not fit other categories"},
]


def get_taxonomy_list() -> list[dict[str, str]]:
    """Return the full taxonomy list."""
    return TAXONOMY


def get_taxonomy_summary() -> str:
    """
    Return a compact text summary of the taxonomy for use in LLM prompts.

    Formatted for minimal token usage while providing enough context
    for the classifier to work.
    """
    lines = []
    for cat in TAXONOMY:
        lines.append(f"{cat['code']}: {cat['segment']} > {cat['family']} > {cat['class']}")
    return "\n".join(lines)


def find_category_by_code(code: str) -> dict[str, str] | None:
    """Look up a category by its code."""
    for cat in TAXONOMY:
        if cat["code"] == code:
            return cat
    return None


# ---------------------------------------------------------------------------
# CLI: print the taxonomy
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Product Taxonomy ===")
    print(f"Total categories: {len(TAXONOMY)}")
    print()
    print(get_taxonomy_summary())
