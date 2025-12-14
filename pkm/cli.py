"""CLI for PKM - Personal Knowledge Management tools."""

import argparse
import sys

from pkm.embeddings import embed_documents, get_or_create_db


def cmd_embed(args):
    """Handle the embed command."""
    result = embed_documents(
        db_path=args.db,
        model_name=args.model,
        limit=args.limit,
        batch_size=args.batch_size
    )
    print(f"\nEmbedding complete:")
    print(f"  Model: {result['model']}")
    print(f"  Documents embedded: {result['embedded']}")


def cmd_init(args):
    """Initialize a new database."""
    conn = get_or_create_db(args.db)
    conn.close()
    print(f"Database initialized: {args.db}")


def cmd_add(args):
    """Add a document to the database."""
    import sqlite3
    conn = get_or_create_db(args.db)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO documents (content, source) VALUES (?, ?)",
        (args.content, args.source)
    )
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"Added document with ID: {doc_id}")


def cmd_stats(args):
    """Show database statistics."""
    import sqlite3
    conn = get_or_create_db(args.db)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]

    cursor.execute("SELECT model_name, COUNT(*) FROM embeddings GROUP BY model_name")
    embedding_stats = cursor.fetchall()

    conn.close()

    print(f"Database: {args.db}")
    print(f"Total documents: {doc_count}")
    print("Embeddings by model:")
    for model, count in embedding_stats:
        print(f"  {model}: {count}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="pkm",
        description="Personal Knowledge Management tools"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # embed command
    embed_parser = subparsers.add_parser("embed", help="Embed documents using sentence transformers")
    embed_parser.add_argument("--db", required=True, help="Path to SQLite database")
    embed_parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="HuggingFace model name (default: sentence-transformers/all-MiniLM-L6-v2)"
    )
    embed_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of documents to embed"
    )
    embed_parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding (default: 32)"
    )
    embed_parser.set_defaults(func=cmd_embed)

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize a new database")
    init_parser.add_argument("--db", required=True, help="Path to SQLite database")
    init_parser.set_defaults(func=cmd_init)

    # add command
    add_parser = subparsers.add_parser("add", help="Add a document to the database")
    add_parser.add_argument("--db", required=True, help="Path to SQLite database")
    add_parser.add_argument("--content", required=True, help="Document content")
    add_parser.add_argument("--source", default=None, help="Document source")
    add_parser.set_defaults(func=cmd_add)

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    stats_parser.add_argument("--db", required=True, help="Path to SQLite database")
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
