import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "gapmind.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS research_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT,
                content TEXT NOT NULL,
                published_date TEXT,
                FOREIGN KEY (run_id) REFERENCES research_runs(id)
            );

            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                source_id INTEGER NOT NULL,
                claim_text TEXT NOT NULL,
                claim_type TEXT DEFAULT 'statement',
                confidence TEXT DEFAULT 'unassessed',
                FOREIGN KEY (run_id) REFERENCES research_runs(id),
                FOREIGN KEY (source_id) REFERENCES sources(id)
            );

            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES research_runs(id)
            );
        """)


def create_research_run(topic):
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO research_runs (topic, created_at) VALUES (?, ?)",
            (topic, datetime.now(timezone.utc).isoformat())
        )
        return cursor.lastrowid


def save_source(run_id, source):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO sources
            (run_id, title, source_type, source_url, content, published_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                source.get("title", "Untitled source"),
                source.get("source_type", "text"),
                source.get("url"),
                source.get("content", ""),
                source.get("published_date")
            )
        )
        return cursor.lastrowid


def save_claims(run_id, claims):
    with get_connection() as connection:
        for claim in claims:
            connection.execute(
                """
                INSERT INTO claims
                (run_id, source_id, claim_text, claim_type, confidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    claim["source_id"],
                    claim["claim_text"],
                    claim.get("claim_type", "statement"),
                    claim.get("confidence", "unassessed")
                )
            )


def save_analysis(run_id, result):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO analysis_results (run_id, result_json, created_at)
            VALUES (?, ?, ?)
            """,
            (
                run_id,
                json.dumps(result, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat()
            )
        )


def get_recent_runs(limit=10):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, topic, created_at
            FROM research_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]