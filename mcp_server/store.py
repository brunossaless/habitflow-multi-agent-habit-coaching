"""SQLite-backed HabitFlow Kanban board + habit storage (MCP layer)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

DB_PATH = Path(__file__).parent.parent / "data" / "habitflow.db"

COLUMNS = ["backlog", "todo", "in_progress", "review", "done"]

ROUTING = {
    "collect": "collector-agent",
    "checkin": "collector-agent",
    "persist": "collector-agent",
    "extract": "analyzer-agent",
    "metrics": "analyzer-agent",
    "nlp": "analyzer-agent",
    "coach": "coach-agent",
    "insights": "coach-agent",
    "patterns": "coach-agent",
    "rag": "coach-agent",
    "guardian": "guardian-agent",
    "safety": "guardian-agent",
    "compliance": "guardian-agent",
    "notify": "notifier-agent",
    "feedback": "notifier-agent",
    "push": "notifier-agent",
}


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                labels TEXT,
                points INTEGER DEFAULT 1,
                column_id TEXT DEFAULT 'backlog',
                assignee TEXT,
                executed_by TEXT,
                result TEXT,
                sprint TEXT DEFAULT 'Habit Sprint',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT,
                action TEXT,
                card_id TEXT,
                payload TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS habit_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                entries TEXT,
                mood_emoji TEXT,
                timestamp TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                action TEXT,
                user_id TEXT,
                payload_hash TEXT,
                reasoning TEXT,
                created_at TEXT
            );
            """
        )


def route_card(labels: List[str]) -> str:
    for label in labels:
        if label in ROUTING:
            return ROUTING[label]
    return "analyzer-agent"


def board_get() -> Dict[str, Any]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM cards ORDER BY created_at").fetchall()
    cards_by_col: Dict[str, list] = {col: [] for col in COLUMNS}
    for r in rows:
        card = _row_to_card(r)
        col = card.get("column", "backlog")
        if col in cards_by_col:
            cards_by_col[col].append(card)
    columns = [
        {"id": col, "name": col.replace("_", " ").title(), "cards": cards_by_col[col]}
        for col in COLUMNS
    ]
    return {"sprint": "Habit Sprint", "columns": columns}


def card_create(
    actor: str,
    title: str,
    labels: List[str],
    description: str = "",
    points: int = 1,
) -> Dict[str, Any]:
    card_id = f"HF-{uuid4().hex[:4].upper()}"
    now = datetime.utcnow().isoformat()
    with _conn() as c:
        c.execute(
            """INSERT INTO cards (id, title, description, labels, points, column_id, created_at)
               VALUES (?, ?, ?, ?, ?, 'backlog', ?)""",
            (card_id, title, description, json.dumps(labels), points, now),
        )
    activity_log(actor, "card.create", card_id, {"title": title, "labels": labels})
    return {"cardId": card_id, "title": title, "labels": labels}


def card_assign(actor: str, card_id: str, assignee: str) -> Dict[str, Any]:
    with _conn() as c:
        c.execute("UPDATE cards SET assignee=? WHERE id=?", (assignee, card_id))
    activity_log(actor, "card.assign", card_id, {"assignee": assignee})
    return {"cardId": card_id, "assignee": assignee}


def card_move(actor: str, card_id: str, to_column: str) -> Dict[str, Any]:
    if to_column not in COLUMNS:
        raise ValueError(f"Invalid column: {to_column}")
    with _conn() as c:
        c.execute("UPDATE cards SET column_id=? WHERE id=?", (to_column, card_id))
    activity_log(actor, "card.move", card_id, {"toColumn": to_column})
    return {"cardId": card_id, "toColumn": to_column}


def card_comment(actor: str, card_id: str, text: str) -> Dict[str, Any]:
    activity_log(actor, "card.comment", card_id, {"text": text})
    return {"cardId": card_id, "comment": text}


def card_set_result(card_id: str, executed_by: str, result: Dict[str, Any]) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE cards SET executed_by=?, result=? WHERE id=?",
            (executed_by, json.dumps(result, default=str), card_id),
        )


def activity_log(actor: str, action: str, card_id: str, payload: Dict[str, Any]) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO activity (actor, action, card_id, payload, created_at) VALUES (?,?,?,?,?)",
            (actor, action, card_id, json.dumps(payload), datetime.utcnow().isoformat()),
        )


def get_activity(limit: int = 100) -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def reset_board() -> None:
    with _conn() as c:
        c.execute("DELETE FROM cards")
        c.execute("DELETE FROM activity")


def save_habit_log(user_id: str, entries: list, mood: Optional[str], ts: str) -> str:
    log_id = str(uuid4())
    with _conn() as c:
        c.execute(
            "INSERT INTO habit_logs (id, user_id, entries, mood_emoji, timestamp) VALUES (?,?,?,?,?)",
            (log_id, user_id, json.dumps(entries), mood, ts),
        )
    return log_id


def get_habit_logs(user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM habit_logs WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def _row_to_card(row: sqlite3.Row) -> Dict[str, Any]:
    result = None
    if row["result"]:
        try:
            result = json.loads(row["result"])
        except json.JSONDecodeError:
            result = {"raw": row["result"]}
    labels = json.loads(row["labels"]) if row["labels"] else []
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"] or "",
        "labels": labels,
        "points": row["points"],
        "column": row["column_id"],
        "assignee": row["assignee"],
        "executedBy": row["executed_by"],
        "result": result,
    }
