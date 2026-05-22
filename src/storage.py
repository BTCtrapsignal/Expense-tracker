"""
Storage — SQLite with full column schema (no JSON blob).
"""

import sqlite3
import os
from datetime import date, datetime

DB_PATH = os.environ.get("DB_PATH", "expenses.db")

DDL = """
CREATE TABLE IF NOT EXISTS entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT    NOT NULL,
    day             TEXT    NOT NULL,
    chat_id         INTEGER NOT NULL,
    raw_text        TEXT    NOT NULL,
    merchant_code   TEXT    NOT NULL,
    merchant_name   TEXT    NOT NULL,
    card_code       TEXT    NOT NULL,
    card_name       TEXT    NOT NULL,
    amount          REAL    NOT NULL,
    is_installment  INTEGER NOT NULL DEFAULT 0,
    full_amount     REAL,
    months          INTEGER,
    monthly_amount  REAL,
    note            TEXT
)
"""

# Migration: add note column to existing DB that was created without it
MIGRATE_NOTE = "ALTER TABLE entries ADD COLUMN note TEXT"


def _row_to_dict(row) -> dict:
    keys = [
        "id", "ts", "day", "chat_id", "raw_text",
        "merchant_code", "merchant_name",
        "card_code", "card_name",
        "amount", "is_installment", "full_amount", "months", "monthly_amount",
        "note",
    ]
    d = dict(zip(keys, row))
    d["is_installment"] = bool(d["is_installment"])
    # compatibility shims for formatter
    d["type"]     = "installment" if d["is_installment"] else "normal"
    d["merchant"] = d["merchant_name"]
    d["monthly"]  = d["monthly_amount"]
    return d


class Storage:
    def __init__(self):
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._conn.execute(DDL)
        self._conn.commit()
        self._migrate()

    def _migrate(self):
        """Add columns introduced after initial deploy."""
        try:
            self._conn.execute(MIGRATE_NOTE)
            self._conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists

    def add(self, entry: dict, chat_id: int = 0):
        is_inst = entry["type"] == "installment"
        self._conn.execute(
            """INSERT INTO entries
               (ts, day, chat_id, raw_text,
                merchant_code, merchant_name, card_code, card_name,
                amount, is_installment, full_amount, months, monthly_amount, note)
               VALUES (?,?,?,?, ?,?,?,?, ?,?,?,?,?,?)""",
            (
                datetime.utcnow().isoformat(),
                date.today().isoformat(),
                chat_id,
                entry.get("raw", ""),
                entry["merchant_code"],
                entry["merchant"],          # already includes note in display name
                entry["card_code"],
                entry["card_name"],
                entry["amount"],
                1 if is_inst else 0,
                entry["amount"]  if is_inst else None,
                entry["months"]  if is_inst else None,
                entry["monthly"] if is_inst else None,
                entry.get("note"),
            ),
        )
        self._conn.commit()

    def get_today(self, chat_id: int = 0) -> list[dict]:
        day = date.today().isoformat()
        if chat_id:
            rows = self._conn.execute(
                "SELECT * FROM entries WHERE day=? AND chat_id=? ORDER BY id",
                (day, chat_id),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM entries WHERE day=? ORDER BY id", (day,)
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def clear_today(self, chat_id: int = 0):
        day = date.today().isoformat()
        if chat_id:
            self._conn.execute(
                "DELETE FROM entries WHERE day=? AND chat_id=?", (day, chat_id)
            )
        else:
            self._conn.execute("DELETE FROM entries WHERE day=?", (day,))
        self._conn.commit()

    def undo_latest(self, chat_id: int = 0) -> dict | None:
        day = date.today().isoformat()
        if chat_id:
            row = self._conn.execute(
                "SELECT * FROM entries WHERE day=? AND chat_id=? ORDER BY id DESC LIMIT 1",
                (day, chat_id),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM entries WHERE day=? ORDER BY id DESC LIMIT 1", (day,)
            ).fetchone()
        if not row:
            return None
        entry = _row_to_dict(row)
        self._conn.execute("DELETE FROM entries WHERE id=?", (entry["id"],))
        self._conn.commit()
        return entry

    def get_week(self, monday_iso: str, sunday_iso: str, chat_id: int = 0) -> list[dict]:
        """Return all entries between monday and sunday inclusive, ordered by day then id."""
        if chat_id:
            rows = self._conn.execute(
                "SELECT * FROM entries WHERE day>=? AND day<=? AND chat_id=? ORDER BY day, id",
                (monday_iso, sunday_iso, chat_id),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM entries WHERE day>=? AND day<=? ORDER BY day, id",
                (monday_iso, sunday_iso),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_distinct_chat_ids(self) -> list[int]:
        """Return all unique chat_ids that have entries (for scheduled broadcast)."""
        rows = self._conn.execute(
            "SELECT DISTINCT chat_id FROM entries WHERE chat_id != 0"
        ).fetchall()
        return [r[0] for r in rows]

    def get_date(self, iso_date: str, chat_id: int = 0) -> list[dict]:
        if chat_id:
            rows = self._conn.execute(
                "SELECT * FROM entries WHERE day=? AND chat_id=? ORDER BY id",
                (iso_date, chat_id),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM entries WHERE day=? ORDER BY id", (iso_date,)
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
