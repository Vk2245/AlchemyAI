"""
Graph-Based Collusion Detection.

Builds a lightweight in-memory graph of Vendors, Addresses, and Emails.
If a new document shares an address or email with a DIFFERENT vendor,
it flags it as a potential collusion risk.
"""

import networkx as nx
from typing import Any

from extraction.schema_models import DocumentRecord

# In-memory graph (Mocking a Neo4j DB for the Hackathon)
G = nx.Graph()


def detect_collusion(record: DocumentRecord) -> dict[str, Any]:
    """
    Checks the document against the global graph for collusion.
    Returns a dict with collusion signals.
    """
    vendor = record.primary_party
    if not vendor:
        return {"is_collusion": False, "collusion_flags": []}
        
    vendor_node = f"VENDOR:{vendor.strip().lower()}"
    
    # Extract addresses and emails from entities
    addresses = [e.value for e in record.entities if e.entity_type == "GPE" or "address" in getattr(e, 'entity_type', '').lower()]
    emails = [e.value for e in record.entities if e.entity_type == "EMAIL" or "@" in e.value]
    
    collusion_flags = []
    
    # Check Addresses
    for addr in set(addresses):
        addr_node = f"ADDR:{addr.strip().lower()}"
        if G.has_node(addr_node):
            # Check if this address is linked to OTHER vendors
            linked_vendors = [n for n in G.neighbors(addr_node) if n.startswith("VENDOR:") and n != vendor_node]
            if linked_vendors:
                names = [v.replace("VENDOR:", "") for v in linked_vendors]
                collusion_flags.append(f"Address '{addr}' is also used by competing vendors: {', '.join(names)}.")
        
        # Add to graph
        G.add_edge(vendor_node, addr_node)
        
    # Check Emails
    for email in set(emails):
        email_node = f"EMAIL:{email.strip().lower()}"
        if G.has_node(email_node):
            linked_vendors = [n for n in G.neighbors(email_node) if n.startswith("VENDOR:") and n != vendor_node]
            if linked_vendors:
                names = [v.replace("VENDOR:", "") for v in linked_vendors]
                collusion_flags.append(f"Email '{email}' is used by other vendors: {', '.join(names)}.")
                
        # Add to graph
        G.add_edge(vendor_node, email_node)
        
    return {
        "is_collusion": len(collusion_flags) > 0,
        "collusion_flags": collusion_flags
    }
