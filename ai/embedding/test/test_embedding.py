#!/usr/bin/env python3
import argparse
import os

import psycopg2
import requests
from pgvector.psycopg2 import register_vector

# --- Configuration ---
TEI_EMBED_URL = "http://localhost:4001"
TEI_RERANK_URL = "http://localhost:4002"
VECTOR_SIZE = 768

# --- DB Configuration ---
PG_HOST = os.environ.get("POSTGRES_HOST", "localhost")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
PG_USER = os.environ.get("POSTGRES_USER", "postgres")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
PG_DB = os.environ.get("POSTGRES_DB", "vectorchord")
TABLE_NAME = "knowledge_embeddings"


def get_db_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DB,
    )


def get_embedding(text):
    """Fetch embedding from TEI /embed endpoint."""
    response = requests.post(
        f"{TEI_EMBED_URL}/embed",
        json={"inputs": text},
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    # TEI returns a list of lists of floats: [[0.1, 0.2, ...]]
    return response.json()[0]


def rerank(query, documents):
    """Fetch reranked results from TEI /rerank endpoint."""
    payload = {
        "query": query,
        "texts": documents,
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


def setup_database():
    """Ensure pgvector extension is created and recreate the embedding table."""
    conn = get_db_connection()
    conn.autocommit = True
    with conn.cursor() as cur:
        # Create extension if not exists
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        # Drop table if exists to start fresh
        cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")
        # Recreate table
        cur.execute(
            f"CREATE TABLE {TABLE_NAME} ("
            f"    id SERIAL PRIMARY KEY,"
            f"    text TEXT NOT NULL,"
            f"    embedding VECTOR({VECTOR_SIZE})"
            f");"
        )
    conn.close()


def embed_file(file_path):
    """Read a file, chunk appropriately, generate embeddings, and save to pgvector."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    setup_database()

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse based on file type
    if file_path.endswith(".md"):
        # Chunk by paragraph for markdown files to maintain context
        raw_chunks = [p.strip() for p in content.split("\n\n") if p.strip()]
        chunks = []
        for chunk in raw_chunks:
            # Skip horizontal lines, title headers, and metadata sections
            if (
                chunk.startswith("---")
                or chunk.startswith("# ")
                or chunk.startswith("## ")
                or chunk.startswith("### ")
                or chunk.startswith("#### ")
            ):
                continue
            chunks.append(chunk)
    else:
        # Standard line-by-line fallback
        chunks = [p.strip() for p in content.split("\n") if p.strip()]

    print(f"🚀 Embedding {len(chunks)} chunks from {file_path}...")

    conn = get_db_connection()
    conn.autocommit = True
    register_vector(conn)

    with conn.cursor() as cur:
        for chunk in chunks:
            vector = get_embedding(chunk)
            cur.execute(
                f"INSERT INTO {TABLE_NAME} (text, embedding) VALUES (%s, %s);",
                (chunk, vector),
            )

    conn.close()
    print(f"✅ Success! Data indexed in table: {TABLE_NAME}")


def query_collection(query_text):
    """Search pgvector using cosine distance and then apply Reranker."""
    query_vector = get_embedding(query_text)

    conn = get_db_connection()
    register_vector(conn)

    with conn.cursor() as cur:
        # Cosine distance operator is <=>
        # Convert distance to similarity score: similarity = 1 - distance
        cur.execute(
            f"SELECT text, 1.0 - (embedding <=> %s) AS score FROM {TABLE_NAME} "
            f"ORDER BY embedding <=> %s LIMIT 10;",
            (query_vector, query_vector),
        )
        results = cur.fetchall()

    conn.close()

    if not results:
        print("❓ No results found in PostgreSQL.")
        return

    retrieved_docs = [row[0] for row in results]

    print(f"\n🔍 [PostgreSQL Retrieval (pgvector)] Query: '{query_text}'")
    for text, score in results[:3]:
        print(f" - [{score:.4f}] {text[:80]}...")

    print("\n⚖️ [TEI Reranking] Refining results...")
    reranked = rerank(query_text, retrieved_docs)

    for i, res in enumerate(reranked):
        doc_text = retrieved_docs[res["index"]]
        print(f" {i + 1}. [Score: {res['score']:.4f}] {doc_text[:100]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TEI and pgvector Diagnostic Tool")
    default_path = os.path.join(os.path.dirname(__file__), "test_snippets.md")
    parser.add_argument(
        "--embed",
        type=str,
        nargs="?",
        const=default_path,
        help="Path to text file to embed (defaults to test/test_snippets.md if flag is present but no path is provided)",
    )
    parser.add_argument("--query", type=str, help="Search query string")

    args = parser.parse_args()

    try:
        # If --embed flag is provided (could be empty/const, or a path string)
        if args.embed is not None:
            embed_file(args.embed)
        elif args.query:
            query_collection(args.query)
        else:
            parser.print_help()
    except Exception as e:
        print(f"❌ Error: {e}")
