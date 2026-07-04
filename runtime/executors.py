"""Specialist execution — real habit processing logic."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mcp_server.store import get_habit_logs, save_habit_log

CRISIS_KEYWORDS = ["não aguento mais", "quero morrer", "suicid"]


def execute_collector(payload: Dict[str, Any]) -> Dict[str, Any]:
    user_id = payload.get("user_id", "demo-user")
    entries = payload.get("entries", [])
    mood = payload.get("mood_emoji")
    ts = payload.get("timestamp", datetime.utcnow().isoformat())
    log_id = save_habit_log(user_id, entries, mood, ts)
    return {
        "executedBy": "collector-agent",
        "log_id": log_id,
        "entries_saved": len(entries),
        "artifacts": [f"data/checkin-{ts[:10]}.json"],
        "notes": f"Check-in persistido com {len(entries)} entrada(s).",
    }


def execute_analyzer(payload: Dict[str, Any]) -> Dict[str, Any]:
    note = payload.get("note", "")
    habit_id = payload.get("habit_id", "exercise")
    metrics: Dict[str, Any] = {}
    confidence = 0.95
    requires_confirmation = False

    if note:
        note_lower = note.lower()
        km = re.search(r"(\d+(?:[.,]\d+)?)\s*km", note_lower)
        if km:
            metrics["distance_km"] = float(km.group(1).replace(",", "."))
            confidence = 0.94
        water = re.search(r"(\d+(?:[.,]\d+)?)\s*l", note_lower)
        if water:
            metrics["water_liters"] = float(water.group(1).replace(",", "."))
            confidence = 0.96
        mins = re.search(r"(\d+)\s*min", note_lower)
        if mins:
            metrics["duration_min"] = int(mins.group(1))
        if re.search(r"fiz algo|algo de exercício", note_lower):
            confidence = 0.65
            requires_confirmation = True

    return {
        "executedBy": "analyzer-agent",
        "metrics": metrics,
        "confidence": confidence,
        "requires_confirmation": requires_confirmation,
        "artifacts": ["output/metrics.json"],
        "notes": f"Métricas extraídas com confiança {confidence:.0%}.",
    }


def execute_coach(payload: Dict[str, Any]) -> Dict[str, Any]:
    user_id = payload.get("user_id", "demo-user")
    logs = get_habit_logs(user_id, limit=14)
    insights: List[Dict[str, Any]] = []
    suggestions: List[Dict[str, Any]] = []

    if len(logs) < 3:
        suggestions.append({
            "action": "Continue registrando seus hábitos diariamente",
            "reasoning": "Dados insuficientes para análise de padrões.",
            "priority": "low",
        })
    else:
        tuesday_issues = _count_tuesday_pattern(logs)
        if tuesday_issues >= 2:
            insights.append({
                "pattern": "Sono < 6h correlaciona com menos exercício nas terças",
                "confidence": 0.91,
                "category": "sleep",
            })
            suggestions.append({
                "action": "Antecipar horário de dormir em 30min nas terças",
                "reasoning": "Padrão detectado em terças recentes",
                "priority": "high",
            })
        else:
            insights.append({
                "pattern": f"{len(logs)} registros analisados — boa consistência",
                "confidence": 0.85,
                "category": "general",
            })
            suggestions.append({
                "action": "Mantenha a rotina atual",
                "reasoning": "Aderência estável nos últimos dias",
                "priority": "medium",
            })

    return {
        "executedBy": "coach-agent",
        "insights": insights,
        "suggestions": suggestions,
        "artifacts": ["output/coach-report.md"],
        "notes": f"{len(insights)} insight(s), {len(suggestions)} sugestão(ões).",
    }


def execute_guardian(payload: Dict[str, Any]) -> Dict[str, Any]:
    suggestions = payload.get("suggestions", [])
    user_notes = payload.get("user_notes", "")
    combined = " ".join(
        s.get("action", "") + " " + s.get("reasoning", "") for s in suggestions
    ).lower()

    for kw in CRISIS_KEYWORDS:
        if kw in user_notes.lower() or kw in combined:
            return {
                "executedBy": "guardian-agent",
                "approved": False,
                "risk_score": 0.95,
                "human_handoff_required": True,
                "warnings": ["Crisis keywords — human handoff"],
                "notes": "Handoff humano necessário.",
            }

    for s in suggestions:
        text = (s.get("action", "") + " " + s.get("reasoning", "")).lower()
        if re.search(r"durm[aá]\s+(?:apenas|s[oó])\s+(\d+)", text):
            m = re.search(r"durm[aá]\s+(?:apenas|s[oó])\s+(\d+)", text)
            if m and int(m.group(1)) < 5:
                return {
                    "executedBy": "guardian-agent",
                    "approved": False,
                    "risk_score": 0.7,
                    "warnings": ["Recomendação de sono insegura bloqueada"],
                    "notes": "Sugestão bloqueada pelo guardião.",
                }

    return {
        "executedBy": "guardian-agent",
        "approved": True,
        "risk_score": 0.1,
        "warnings": [],
        "notes": "Todas as sugestões aprovadas.",
    }


def execute_notifier(payload: Dict[str, Any]) -> Dict[str, Any]:
    insights = payload.get("insights", [])
    suggestions = payload.get("suggestions", [])
    lines = ["📊 Resumo do seu coach de hábitos:\n"]
    for i in insights:
        lines.append(f"• {i.get('pattern', '')}")
    if suggestions:
        lines.append("\n💡 Sugestões:")
        for s in suggestions:
            lines.append(f"• {s.get('action', '')}")
    message = "\n".join(lines)
    return {
        "executedBy": "notifier-agent",
        "delivered": True,
        "message": message,
        "channel": "push",
        "artifacts": ["output/notification.txt"],
        "notes": "Feedback entregue ao usuário.",
    }


EXECUTORS = {
    "collector-agent": execute_collector,
    "analyzer-agent": execute_analyzer,
    "coach-agent": execute_coach,
    "guardian-agent": execute_guardian,
    "notifier-agent": execute_notifier,
}


def run_specialist(agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    fn = EXECUTORS.get(agent_id)
    if not fn:
        return {"executedBy": agent_id, "error": "unknown agent"}
    return fn(payload)


def _count_tuesday_pattern(logs: List[Dict[str, Any]]) -> int:
    issues = 0
    for log in logs:
        try:
            ts = datetime.fromisoformat(log["timestamp"])
        except (KeyError, ValueError):
            continue
        if ts.weekday() != 1:
            continue
        entries = json.loads(log.get("entries", "[]"))
        sleep_h = None
        exercised = False
        for e in entries:
            if e.get("habit_id") == "sleep":
                sleep_h = float(e.get("value", 0) or 0)
            if e.get("habit_id") == "exercise":
                exercised = bool(e.get("value"))
        if sleep_h and sleep_h < 6 and not exercised:
            issues += 1
    return issues


def seed_demo_logs(user_id: str) -> None:
    if get_habit_logs(user_id):
        return
    base = datetime.utcnow() - timedelta(days=14)
    for day in range(14):
        ts = (base + timedelta(days=day)).isoformat()
        is_tue = (base + timedelta(days=day)).weekday() == 1
        sleep = 5.0 if is_tue and day > 7 else 7.5
        exercised = not (is_tue and day > 7)
        entries = [
            {"habit_id": "sleep", "value": sleep, "note": f"Dormi {sleep}h"},
            {
                "habit_id": "exercise",
                "value": exercised,
                "note": "Corri 3km" if exercised else "Cansado, não exercitei",
            },
            {"habit_id": "water", "value": True, "note": "Bebi 2L"},
        ]
        save_habit_log(user_id, entries, "😴" if not exercised else "💪", ts)
