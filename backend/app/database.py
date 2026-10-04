"""SQLite persistence layer (B11)."""
from __future__ import annotations
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "creditpath.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS consent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            action TEXT NOT NULL,          -- 'consent' or 'opt-out'
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS config_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_json TEXT NOT NULL,
            changed_by TEXT NOT NULL DEFAULT 'system',
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS kill_switch_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_json TEXT NOT NULL,
            changed_by TEXT NOT NULL DEFAULT 'system',
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def log_audit(event_type: str, details: str) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (event_type, details, timestamp) VALUES (?, ?, ?)",
        (event_type, details, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def log_consent(customer_id: str, action: str) -> None:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO consent_log (customer_id, action, timestamp) VALUES (?, ?, ?)",
        (customer_id, action, now),
    )
    conn.commit()
    conn.close()
    log_audit("consent", json.dumps({"customer_id": customer_id, "action": action}))


def save_config_version(config_dict: dict, changed_by: str = "system") -> None:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO config_versions (config_json, changed_by, timestamp) VALUES (?, ?, ?)",
        (json.dumps(config_dict), changed_by, now),
    )
    conn.commit()
    conn.close()
    log_audit("config_change", json.dumps({"changed_by": changed_by}))

def save_kill_switch(state: dict, changed_by: str = "system") -> None:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO kill_switch_log (state_json, changed_by, timestamp) VALUES (?, ?, ?)",
        (json.dumps(state), changed_by, now),
    )
    conn.commit()
    conn.close()
    log_audit("kill_switch", json.dumps({"changed_by": changed_by, "state": state}))


def get_audit_log() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT event_type, details, timestamp FROM audit_log ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_consent_status(customer_id: str) -> str | None:
    conn = get_db()
    row = conn.execute(
        "SELECT action FROM consent_log WHERE customer_id = ? ORDER BY id DESC LIMIT 1",
        (customer_id,),
    ).fetchone()
    conn.close()
    return row["action"] if row else None
