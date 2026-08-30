"""
Embed text snippets for software product matching.

Embeds config lines, error logs, version strings, and other text
snippets into the text embedding index so they can be matched to
the nearest catalog record.
"""

import sys
import json
from typing import Any, Optional

import chromadb

from config.settings import CHROMA_DB_DIR
from config.llm_client import get_embedding


SNIPPET_COLLECTION_NAME = "text_snippets"


def get_snippet_collection(
    client: Optional[chromadb.ClientAPI] = None,
) -> chromadb.Collection:
    """Get or create the text snippets collection."""
    if client is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    return client.get_or_create_collection(
        name=SNIPPET_COLLECTION_NAME,
        metadata={"description": "Text snippet embeddings for software product matching"},
    )


def embed_text_snippet(
    snippet: str,
    record_id: str,
    product_name: str = "",
    snippet_type: str = "generic",
    collection: Optional[chromadb.Collection] = None,
) -> None:
    """
    Embed a text snippet (config line, error log, version string) linked
    to a product record.
    """
    if collection is None:
        collection = get_snippet_collection()

    embedding = get_embedding(snippet)

    snippet_id = f"{record_id}_{hash(snippet) % 100000}"

    collection.upsert(
        ids=[snippet_id],
        embeddings=[embedding],
        documents=[snippet],
        metadatas=[{
            "record_id": record_id,
            "product_name": product_name,
            "snippet_type": snippet_type,
        }],
    )


def embed_snippets_batch(
    snippets: list[dict[str, str]],
    record_id: str,
    product_name: str = "",
) -> int:
    """
    Embed a batch of text snippets for a product.

    Each snippet dict should have 'text' and optionally 'type' keys.
    """
    collection = get_snippet_collection()
    count = 0

    for snip in snippets:
        text = snip.get("text", "")
        if not text.strip():
            continue

        try:
            embed_text_snippet(
                snippet=text,
                record_id=record_id,
                product_name=product_name,
                snippet_type=snip.get("type", "generic"),
                collection=collection,
            )
            count += 1
        except Exception as e:
            print(f"  Failed to embed snippet: {e}")

    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m visual_match.embed_text_snippets <snippet_text> <record_id>")
        sys.exit(1)

    snippet = sys.argv[1]
    record_id = sys.argv[2]

    print(f"Embedding snippet: {snippet[:80]}...")
    embed_text_snippet(snippet, record_id)
    print("Done.")

    collection = get_snippet_collection()
    print(f"Snippet collection size: {collection.count()}")
