import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "awg.db"


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init() -> None:
    with _db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                email TEXT NOT NULL,
                description TEXT NOT NULL,
                amount TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT,
                decided_at TEXT
            );
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                action TEXT NOT NULL,
                email TEXT,
                amount TEXT,
                verdict TEXT NOT NULL,
                reason TEXT
            );
            """
        )


def log(action: str, email: str, amount: str, verdict: str, reason: str) -> None:
    with _db() as c:
        c.execute(
            "INSERT INTO audit (ts, action, email, amount, verdict, reason) VALUES (?,?,?,?,?,?)",
            (_now(), action, email, amount, verdict, reason),
        )


def spent_today() -> Decimal:
    today = datetime.now(timezone.utc).date().isoformat()
    with _db() as c:
        rows = c.execute(
            "SELECT amount FROM audit WHERE verdict = 'executed' AND ts LIKE ?",
            (today + "%",),
        ).fetchall()
    return sum((Decimal(r["amount"]) for r in rows), Decimal("0"))


def add_approval(email: str, description: str, amount: str, reason: str) -> int:
    with _db() as c:
        cur = c.execute(
            "INSERT INTO approvals (created_at, email, description, amount, status, reason) "
            "VALUES (?,?,?,?, 'pending', ?)",
            (_now(), email, description, amount, reason),
        )
        return cur.lastrowid


def get_approval(approval_id: int) -> dict | None:
    with _db() as c:
        row = c.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
    return dict(row) if row else None


def list_pending() -> list[dict]:
    with _db() as c:
        rows = c.execute("SELECT * FROM approvals WHERE status = 'pending' ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def set_status(approval_id: int, status: str, reason: str) -> None:
    with _db() as c:
        c.execute(
            "UPDATE approvals SET status = ?, reason = ?, decided_at = ? WHERE id = ?",
            (status, reason, _now(), approval_id),
        )