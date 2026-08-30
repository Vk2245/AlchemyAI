"""
Embed catalog product images using nomic-embed-vision-v1.5 locally.

Extracts images from PDFs (via ingestion/parse_pdf) and embeds them
into a separate ChromaDB collection for visual matching.
Runs fully locally via the transformers library.
"""

import sys
import json
from pathlib import Path
from typing import Any, Optional

import chromadb

from config.settings import CHROMA_DB_DIR
from config.llm_client import get_image_embedding


IMAGE_COLLECTION_NAME = "product_images"


def get_image_collection(
    client: Optional[chromadb.ClientAPI] = None,
) -> chromadb.Collection:
    """Get or create the product images embedding collection."""
    if client is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    return client.get_or_create_collection(
        name=IMAGE_COLLECTION_NAME,
        metadata={"description": "Product image embeddings via nomic-embed-vision"},
    )


def embed_product_image(
    image_path: str,
    record_id: str,
    product_name: str = "",
    metadata: dict[str, str] | None = None,
    collection: Optional[chromadb.Collection] = None,
) -> None:
    """
    Embed a single product image into the image collection.
    """
    if collection is None:
        collection = get_image_collection()

    embedding = get_image_embedding(image_path)

    meta = {
        "record_id": record_id,
        "product_name": product_name,
        "image_path": image_path,
    }
    if metadata:
        meta.update(metadata)

    image_id = f"{record_id}_{Path(image_path).stem}"

    collection.upsert(
        ids=[image_id],
        embeddings=[embedding],
        documents=[f"Image of {product_name}"],
        metadatas=[meta],
    )


def embed_images_from_extraction(
    extracted_images: list[dict[str, Any]],
    record_id: str,
    product_name: str = "",
) -> int:
    """
    Embed all images extracted from a PDF during ingestion.

    Takes the list of image dicts from ingestion/parse_pdf.extract_images().
    Returns the number of images successfully embedded.
    """
    collection = get_image_collection()
    count = 0

    for img in extracted_images:
        filepath = img.get("filepath", "")
        if not filepath or not Path(filepath).exists():
            continue

        try:
            embed_product_image(
                image_path=filepath,
                record_id=record_id,
                product_name=product_name,
                metadata={
                    "page_number": str(img.get("page_number", 0)),
                    "width": str(img.get("width", 0)),
                    "height": str(img.get("height", 0)),
                },
                collection=collection,
            )
            count += 1
        except Exception as e:
            print(f"  Failed to embed {filepath}: {e}")

    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m visual_match.embed_product_images <image_path> <record_id> [product_name]")
        sys.exit(1)

    image_path = sys.argv[1]
    record_id = sys.argv[2]
    product_name = sys.argv[3] if len(sys.argv) > 3 else ""

    print(f"Embedding image: {image_path}")
    embed_product_image(image_path, record_id, product_name)
    print("Done.")

    collection = get_image_collection()
    print(f"Image collection size: {collection.count()}")
