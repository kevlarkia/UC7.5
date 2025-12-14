"""Document embedding functionality using sentence transformers."""

import sqlite3
from pathlib import Path
from typing import Optional

from sentence_transformers import SentenceTransformer


def get_or_create_db(db_path: str) -> sqlite3.Connection:
    """Get or create a SQLite database with the required schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            embedding BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id),
            UNIQUE(document_id, model_name)
        )
    """)

    conn.commit()
    return conn


def embed_documents(
    db_path: str,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    limit: Optional[int] = None,
    batch_size: int = 32
) -> dict:
    """
    Embed documents from the database using the specified model.

    Args:
        db_path: Path to the SQLite database
        model_name: HuggingFace model name for sentence transformers
        limit: Maximum number of documents to embed (None for all)
        batch_size: Number of documents to process in each batch

    Returns:
        Dictionary with embedding statistics
    """
    conn = get_or_create_db(db_path)
    cursor = conn.cursor()

    # Load the model
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)

    # Get documents that don't have embeddings for this model yet
    query = """
        SELECT d.id, d.content
        FROM documents d
        LEFT JOIN embeddings e ON d.id = e.document_id AND e.model_name = ?
        WHERE e.id IS NULL
    """
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query, (model_name,))
    documents = cursor.fetchall()

    if not documents:
        print("No documents found to embed.")
        return {"embedded": 0, "model": model_name, "total": 0}

    print(f"Found {len(documents)} documents to embed")

    embedded_count = 0

    # Process in batches
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        doc_ids = [doc[0] for doc in batch]
        contents = [doc[1] for doc in batch]

        # Generate embeddings
        embeddings = model.encode(contents, show_progress_bar=False)

        # Store embeddings
        for doc_id, embedding in zip(doc_ids, embeddings):
            cursor.execute(
                "INSERT OR REPLACE INTO embeddings (document_id, model_name, embedding) VALUES (?, ?, ?)",
                (doc_id, model_name, embedding.tobytes())
            )

        conn.commit()
        embedded_count += len(batch)
        print(f"Embedded {embedded_count}/{len(documents)} documents")

    conn.close()

    return {
        "embedded": embedded_count,
        "model": model_name,
        "total": len(documents)
    }
