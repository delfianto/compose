#!/usr/bin/env python3
import argparse
import os

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# --- Configuration ---
TEI_EMBED_URL = "http://localhost:4000"
TEI_RERANK_URL = "http://localhost:4001"
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "tei_test_collection"
VECTOR_SIZE = 1024

client = QdrantClient(url=QDRANT_URL)


def get_embedding(text):
    """Fetch embedding from TEI /embed endpoint."""
    response = requests.post(
        f"{TEI_EMBED_URL}/embed",
        json={"inputs": text},
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    # TEI returns a list of floats
    return response.json()[0]


def rerank(query, documents):
    """Fetch reranked results from TEI /rerank endpoint."""
    # The error message explicitly asked for 'texts' instead of 'documents'
    payload = {
        "query": query,
        "texts": documents,  # Changed from 'documents' to 'texts'
        "top_n": 5,
    }

    response = requests.post(
        f"{TEI_RERANK_URL}/rerank",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code != 200:
        print(f"DEBUG: TEI rejected payload. Response: {response.text}")
        response.raise_for_status()

    return response.json()


def setup_collection():
    """Fix for DeprecationWarning: Check existence then create."""
    if client.collection_exists(collection_name=COLLECTION_NAME):
        client.delete_collection(collection_name=COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )


def embed_file(file_path):
    """Read a file, chunk by line, and upsert to Qdrant."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    setup_collection()

    with open(file_path, "r") as f:
        # Splitting by double newlines or single lines depending on your generation
        content = f.read()
        lines = [p.strip() for p in content.split("\n") if p.strip()]

    print(f"🚀 Embedding {len(lines)} chunks from {file_path}...")

    points = []
    for i, line in enumerate(lines):
        vector = get_embedding(line)
        points.append(PointStruct(id=i, vector=vector, payload={"text": line}))

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"✅ Success! Data indexed in collection: {COLLECTION_NAME}")


def query_collection(query_text):
    """Search Qdrant using the updated query_points API and then apply Reranker."""
    query_vector = get_embedding(query_text)

    # Fix for 'no attribute search': Use query_points or ensure the client is correctly used
    # query_points is the recommended modern high-level API
    results = client.query_points(
        collection_name=COLLECTION_NAME, query=query_vector, limit=10, with_payload=True
    ).points

    if not results:
        print("❓ No results found in Qdrant.")
        return

    retrieved_docs = [hit.payload["text"] for hit in results]

    print(f"\n🔍 [Qdrant Retrieval] Query: '{query_text}'")
    for hit in results[:3]:
        print(f" - [{hit.score:.4f}] {hit.payload['text'][:80]}...")

    print("\n⚖️ [TEI Reranking] Refining results...")
    reranked = rerank(query_text, retrieved_docs)

    for i, res in enumerate(reranked):
        doc_text = retrieved_docs[res["index"]]
        print(f" {i + 1}. [Score: {res['score']:.4f}] {doc_text[:100]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TEI and Qdrant Diagnostic Tool")
    parser.add_argument("--embed", type=str, help="Path to text file to embed")
    parser.add_argument("--query", type=str, help="Search query string")

    args = parser.parse_args()

    try:
        if args.embed:
            embed_file(args.embed)
        elif args.query:
            query_collection(args.query)
        else:
            parser.print_help()
    except Exception as e:
        print(f"❌ Error: {e}")
