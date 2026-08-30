"""
Unified matching function for "Snap and Find".

Takes either a photo or a text snippet and finds the nearest catalog
match. One function, two input types -- uses the appropriate embedding
model and collection based on input type.
"""

import sys
from pathlib import Path
from typing import Any, Optional

from config.llm_client import get_embedding, get_image_embedding
from visual_match.embed_product_images import get_image_collection
from visual_match.embed_text_snippets import get_snippet_collection
from knowledge.embed_products import query_similar as query_product_index


def match_input(
    input_value: str,
    input_type: str = "auto",
    n_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Match an input (photo path or text snippet) to the nearest catalog records.

    input_type can be:
      - 'auto': detect from the input (file path = image, otherwise text)
      - 'image': treat as an image file path
      - 'text': treat as a text snippet

    Returns a list of matches with product info and similarity scores.
    """
    if input_type == "auto":
        input_type = _detect_input_type(input_value)

    if input_type == "image":
        return _match_image(input_value, n_results)
    else:
        return _match_text(input_value, n_results)


def _detect_input_type(input_value: str) -> str:
    """Detect whether the input is an image path or text snippet."""
    path = Path(input_value)
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    if path.exists() and path.suffix.lower() in image_extensions:
        return "image"
    return "text"


def _match_image(
    image_path: str,
    n_results: int = 5,
) -> list[dict[str, Any]]:
    """Match an image against the product image collection."""
    embedding = get_image_embedding(image_path)

    collection = get_image_collection()
    if collection.count() == 0:
        return []

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
    )

    matches = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i] if results.get("metadatas") else {}
        matches.append({
            "id": results["ids"][0][i],
            "match_type": "image",
            "product_name": meta.get("product_name", ""),
            "record_id": meta.get("record_id", ""),
            "distance": results["distances"][0][i] if results.get("distances") else None,
            "similarity": round(1 - (results["distances"][0][i] if results.get("distances") else 1.0), 3),
        })

    return matches


def _match_text(
    text: str,
    n_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Match a text snippet against both the snippet collection and the
    main product index.
    """
    matches = []

    # Search the snippet collection first (config lines, error logs)
    snippet_collection = get_snippet_collection()
    if snippet_collection.count() > 0:
        embedding = get_embedding(text)
        results = snippet_collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
        )

        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i] if results.get("metadatas") else {}
            matches.append({
                "id": results["ids"][0][i],
                "match_type": "text_snippet",
                "product_name": meta.get("product_name", ""),
                "record_id": meta.get("record_id", ""),
                "snippet_type": meta.get("snippet_type", ""),
                "distance": results["distances"][0][i] if results.get("distances") else None,
                "similarity": round(1 - (results["distances"][0][i] if results.get("distances") else 1.0), 3),
            })

    # Also search the main product index
    product_matches = query_product_index(text, n_results=n_results)
    for pm in product_matches:
        meta = pm.get("metadata", {})
        matches.append({
            "id": pm["id"],
            "match_type": "product_record",
            "product_name": meta.get("product_name", ""),
            "record_id": pm["id"],
            "distance": pm.get("distance"),
            "similarity": round(1 - (pm.get("distance", 1.0)), 3),
        })

    # Sort by similarity and deduplicate by record_id
    matches.sort(key=lambda m: -(m.get("similarity", 0)))
    seen: set[str] = set()
    unique_matches = []
    for m in matches:
        rid = m.get("record_id", m["id"])
        if rid not in seen:
            seen.add(rid)
            unique_matches.append(m)

    return unique_matches[:n_results]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m visual_match.match_input <image_path>")
        print("  python -m visual_match.match_input 'error log text or config line'")
        sys.exit(1)

    input_value = sys.argv[1]
    input_type = _detect_input_type(input_value)
    print(f"Input type: {input_type}")
    print(f"Input: {input_value[:100]}")
    print()

    matches = match_input(input_value)
    print(f"Matches found: {len(matches)}")

    for m in matches:
        print(f"  [{m['match_type']}] {m['product_name']} sim={m['similarity']:.3f}")
