"""
Embeds trusted product records into ChromaDB for similarity search.

This is the shared embedding index used by compatibility, similarity,
discovery, and reasoning modules. Uses nomic-embed-text via Ollama
for local, cost-free embeddings.
"""

import sys
import json
from typing import Any, Optional

import chromadb

from config.settings import CHROMA_DB_DIR
from config.llm_client import get_embedding


# ChromaDB collection name for product records
COLLECTION_NAME = "product_records"


def get_chroma_client() -> chromadb.ClientAPI:
    """Create a persistent ChromaDB client using the configured directory."""
    return chromadb.PersistentClient(path=str(CHROMA_DB_DIR))


def get_collection(
    client: Optional[chromadb.ClientAPI] = None,
) -> chromadb.Collection:
    """Get or create the product records collection."""
    if client is None:
        client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Trusted product record embeddings"},
    )


def record_to_text(record: dict[str, Any]) -> str:
    """
    Convert a product record dict into a text string for embedding.

    Combines the most semantically meaningful fields into one string.
    """
    parts = []

    if record.get("product_name"):
        parts.append(f"Product: {record['product_name']}")
    if record.get("manufacturer"):
        parts.append(f"Manufacturer: {record['manufacturer']}")
    if record.get("description"):
        parts.append(f"Description: {record['description']}")
    if record.get("category"):
        parts.append(f"Category: {record['category']}")
    if record.get("industry"):
        parts.append(f"Industry: {record['industry']}")

    # Add key attributes
    for attr in record.get("attributes", [])[:15]:
        name = attr.get("name", "")
        value = attr.get("value", "")
        unit = attr.get("unit", "")
        parts.append(f"{name}: {value} {unit}".strip())

    return ". ".join(parts)


def embed_record(
    record: dict[str, Any],
    record_id: str,
    collection: Optional[chromadb.Collection] = None,
) -> None:
    """
    Embed a single product record into ChromaDB.

    record_id should be unique (e.g. content_hash or a UUID).
    """
    if collection is None:
        collection = get_collection()

    text = record_to_text(record)
    embedding = get_embedding(text)

    # Store the record data as metadata (ChromaDB metadata must be flat)
    metadata = {
        "product_name": record.get("product_name", ""),
        "manufacturer": record.get("manufacturer", ""),
        "part_number": record.get("part_number", ""),
        "industry": record.get("industry", ""),
        "category": record.get("category", ""),
        "record_confidence": record.get("record_confidence", 0.0),
    }

    collection.upsert(
        ids=[record_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata],
    )


def embed_records_batch(
    records: list[dict[str, Any]],
    record_ids: list[str],
    collection: Optional[chromadb.Collection] = None,
) -> None:
    """
    Embed a batch of product records into ChromaDB.

    More efficient than calling embed_record in a loop.
    """
    if collection is None:
        collection = get_collection()

    texts = [record_to_text(r) for r in records]

    # Embed in batches to avoid memory issues
    from config.llm_client import get_embeddings_batch
    embeddings = get_embeddings_batch(texts)

    metadatas = []
    for record in records:
        metadatas.append({
            "product_name": record.get("product_name", ""),
            "manufacturer": record.get("manufacturer", ""),
            "part_number": record.get("part_number", ""),
            "industry": record.get("industry", ""),
            "category": record.get("category", ""),
            "record_confidence": record.get("record_confidence", 0.0),
        })

    collection.upsert(
        ids=record_ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )


def query_similar(
    query_text: str,
    n_results: int = 5,
    collection: Optional[chromadb.Collection] = None,
    where_filter: Optional[dict] = None,
) -> list[dict[str, Any]]:
    """
    Find the most similar records to a query text.

    Returns a list of result dicts with id, distance, document text,
    and metadata.
    """
    if collection is None:
        collection = get_collection()

    query_embedding = get_embedding(query_text)

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
    }
    if where_filter:
        kwargs["where"] = where_filter

    results = collection.query(**kwargs)

    # Flatten the results into a list of dicts
    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "id": results["ids"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
            "document": results["documents"][0][i] if results.get("documents") else None,
            "metadata": results["metadatas"][0][i] if results.get("metadatas") else None,
        })

    return output


def get_collection_count(
    collection: Optional[chromadb.Collection] = None,
) -> int:
    """Return the number of records in the embedding index."""
    if collection is None:
        collection = get_collection()
    return collection.count()


# ---------------------------------------------------------------------------
# CLI: embed or query the product index
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m knowledge.embed_products embed <record_json>")
        print("  python -m knowledge.embed_products query <search_text>")
        print("  python -m knowledge.embed_products count")
        sys.exit(1)

    command = sys.argv[1]

    if command == "embed":
        record_path = sys.argv[2]
        with open(record_path, "r", encoding="utf-8") as f:
            record = json.load(f)

        record_id = record.get("content_hash", record_path)
        embed_record(record, record_id)
        print(f"Embedded: {record.get('product_name', 'unknown')}")
        print(f"Collection size: {get_collection_count()}")

    elif command == "query":
        query = " ".join(sys.argv[2:])
        print(f"Searching for: {query}")
        results = query_similar(query)

        for r in results:
            print(f"\n  ID: {r['id']}")
            print(f"  Distance: {r['distance']:.4f}")
            meta = r.get("metadata", {})
            print(f"  Product: {meta.get('product_name', '?')}")
            print(f"  Manufacturer: {meta.get('manufacturer', '?')}")

    elif command == "count":
        print(f"Collection size: {get_collection_count()}")
