import sqlite3
import json
import os

_BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DB_PATH         = os.path.join(_BASE_DIR, "db", "telemetry.db")
DB_SCHEME_PATH  = os.path.join(_BASE_DIR, "db", "scheme.sql")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(DB_SCHEME_PATH):
        raise FileNotFoundError(f"{DB_SCHEME_PATH} not found!")

    conn = get_db()
    try:
        with open(DB_SCHEME_PATH, "r") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()
    print("[DB] Database initialized.")


def save_scan(timestamp: str, networks: list):
    """Insert a new scan record into the database."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO scans (timestamp, data) VALUES (?, ?)",
            (timestamp, json.dumps(networks, ensure_ascii=False))
        )
        conn.commit()
    finally:
        conn.close()


def get_scans(from_ts: str = "", to_ts: str = "", limit: int = 100) -> list:
    """Return scan records with optional time range filtering."""
    query = "SELECT id, timestamp, data FROM scans"
    params = []
    clauses = []

    if from_ts:
        clauses.append("timestamp >= ?")
        params.append(from_ts)
    if to_ts:
        clauses.append("timestamp <= ?")
        params.append(to_ts)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    conn = get_db()
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "count": len(json.loads(r["data"]))
        }
        for r in rows
    ]


def get_latest_scan() -> dict | None:
    """Return the most recent scan record, or None if the table is empty."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, timestamp, data FROM scans ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "networks": json.loads(row["data"])
    }