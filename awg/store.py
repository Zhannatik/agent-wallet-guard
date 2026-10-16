import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from awg.policy import Policy

DB_PATH = Path(__file__).resolve().parents[1] / "awg.db"

# В колонке email хранится получатель счёта или capture_id для возврата
_POLICY_KEYS = (
    "max_per_tx", "daily_budget", "approval_threshold",
    "max_refund", "refund_approval_threshold", "daily_refund_budget",
)


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
                kind TEXT NOT NULL DEFAULT 'invoice',
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
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )


def log(action: str, email: str, amount: str, verdict: str, reason: str) -> None:
    with _db() as c:
        c.execute(
            "INSERT INTO audit (ts, action, email, amount, verdict, reason) VALUES (?,?,?,?,?,?)",
            (_now(), action, email, amount, verdict, reason),
        )


def spent_today(action: str = "invoice") -> Decimal:
    today = datetime.now(timezone.utc).date().isoformat()
    with _db() as c:
        rows = c.execute(
            "SELECT amount FROM audit WHERE verdict = 'executed' AND action = ? AND ts LIKE ?",
            (action, today + "%"),
        ).fetchall()
    return sum((Decimal(r["amount"]) for r in rows), Decimal("0"))


def add_approval(kind: str, email: str, description: str, amount: str, reason: str) -> int:
    with _db() as c:
        cur = c.execute(
            "INSERT INTO approvals (created_at, kind, email, description, amount, status, reason) "
            "VALUES (?,?,?,?,?, 'pending', ?)",
            (_now(), kind, email, description, amount, reason),
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


def list_audit(limit: int = 20) -> list[dict]:
    with _db() as c:
        rows = c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def save_policy(p: Policy) -> None:
    data = {k: str(getattr(p, k)) for k in _POLICY_KEYS}
    data["allowed_recipients"] = p.allowed_recipients
    with _db() as c:
        c.execute(
            "INSERT INTO settings (key, value) VALUES ('policy', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (json.dumps(data),),
        )


def load_policy() -> Policy:
    with _db() as c:
        row = c.execute("SELECT value FROM settings WHERE key = 'policy'").fetchone()
    if not row:
        return Policy()
    d = json.loads(row["value"])
    values = {k: Decimal(d[k]) for k in _POLICY_KEYS if k in d}
    return Policy(allowed_recipients=d.get("allowed_recipients", []), **values)