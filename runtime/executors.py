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
    current_metrics = payload.get("current_metrics", {})
    current_note = payload.get("current_note", "")
    logs = get_habit_logs(user_id, limit=30)
    stats = _aggregate_history(logs)
    insights: List[Dict[str, Any]] = []
    suggestions: List[Dict[str, Any]] = []

    primary_action = _build_primary_action(stats, current_metrics, current_note, len(logs))
    insights.extend(_build_insights(stats, logs, len(logs)))
    suggestions.append({
        "action": primary_action["action"],
        "reasoning": primary_action["reasoning"],
        "priority": "high" if primary_action["direction"] != "maintain" else "medium",
    })

    # Secondary suggestions when patterns exist beyond the primary action
    tuesday_issues = _count_tuesday_pattern(logs)
    if tuesday_issues >= 2 and primary_action.get("category") != "sleep":
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

    return {
        "executedBy": "coach-agent",
        "insights": insights,
        "suggestions": suggestions,
        "primary_action": primary_action,
        "stats_snapshot": {
            "logs_analyzed": len(logs),
            "avg_distance_km": stats.get("avg_distance_km"),
            "avg_water_l": stats.get("avg_water_l"),
            "exercise_rate": round(stats.get("exercise_rate", 0), 2),
        },
        "artifacts": ["output/coach-report.md"],
        "notes": f"Recomendação: {primary_action['title']}",
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
    primary = payload.get("primary_action")
    insights = payload.get("insights", [])
    suggestions = payload.get("suggestions", [])

    if primary:
        direction_label = {
            "increase": "Aumentar",
            "decrease": "Reduzir",
            "maintain": "Manter",
        }.get(primary.get("direction", "maintain"), "Agir")
        lines = [
            f"🎯 Melhor ação agora: {primary.get('title', '')}",
            "",
            primary.get("action", ""),
            "",
            f"📌 Tipo: {direction_label} · {primary.get('category', 'geral')}",
            f"💡 {primary.get('reasoning', '')}",
        ]
    else:
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
        "primary_action": primary,
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


def _parse_log_metrics(log: Dict[str, Any]) -> Dict[str, Any]:
    entries = json.loads(log.get("entries", "[]"))
    note = " ".join(str(e.get("note", "")) for e in entries)
    note_lower = note.lower()
    metrics: Dict[str, Any] = {"exercised": False}

    km = re.search(r"(\d+(?:[.,]\d+)?)\s*km", note_lower)
    if km:
        metrics["distance_km"] = float(km.group(1).replace(",", "."))
        metrics["exercised"] = True
    water = re.search(r"(\d+(?:[.,]\d+)?)\s*l", note_lower)
    if water:
        metrics["water_liters"] = float(water.group(1).replace(",", "."))
    sleep_note = re.search(r"(\d+(?:[.,]\d+)?)\s*h(?:\s+de\s+sono|\s+dormi)?", note_lower)
    if sleep_note:
        metrics["sleep_hours"] = float(sleep_note.group(1).replace(",", "."))

    for e in entries:
        habit = e.get("habit_id")
        if habit == "sleep" and e.get("value") is not None:
            try:
                metrics["sleep_hours"] = float(e.get("value") or 0)
            except (TypeError, ValueError):
                pass
        if habit == "exercise":
            if e.get("value"):
                metrics["exercised"] = True
        if habit == "water" and e.get("value"):
            metrics["had_water"] = True

    return metrics


def _aggregate_history(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    distances: List[float] = []
    waters: List[float] = []
    sleep_hours: List[float] = []
    exercise_days = 0

    for log in logs:
        m = _parse_log_metrics(log)
        if m.get("distance_km") is not None:
            distances.append(m["distance_km"])
        if m.get("water_liters") is not None:
            waters.append(m["water_liters"])
        if m.get("sleep_hours") is not None:
            sleep_hours.append(m["sleep_hours"])
        if m.get("exercised"):
            exercise_days += 1

    recent_exercise = 0
    for log in logs[:5]:
        if _parse_log_metrics(log).get("exercised"):
            recent_exercise += 1

    return {
        "log_count": len(logs),
        "avg_distance_km": round(sum(distances) / len(distances), 2) if distances else None,
        "last_distance_km": distances[0] if distances else None,
        "max_distance_km": max(distances) if distances else None,
        "avg_water_l": round(sum(waters) / len(waters), 2) if waters else None,
        "last_water_l": waters[0] if waters else None,
        "avg_sleep_h": round(sum(sleep_hours) / len(sleep_hours), 2) if sleep_hours else None,
        "last_sleep_h": sleep_hours[0] if sleep_hours else None,
        "exercise_rate": exercise_days / len(logs) if logs else 0.0,
        "recent_exercise_days": recent_exercise,
        "distance_samples": len(distances),
        "water_samples": len(waters),
    }


def _build_insights(
    stats: Dict[str, Any], logs: List[Dict[str, Any]], log_count: int
) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    if log_count < 3:
        insights.append({
            "pattern": "Histórico ainda curto — registre mais dias para recomendações precisas",
            "confidence": 0.95,
            "category": "data",
        })
        return insights

    if stats.get("avg_distance_km"):
        insights.append({
            "pattern": f"Média de corrida: {stats['avg_distance_km']} km em {stats['distance_samples']} registro(s)",
            "confidence": 0.9,
            "category": "exercise",
        })
    if stats.get("avg_water_l"):
        insights.append({
            "pattern": f"Média de água: {stats['avg_water_l']} L/dia",
            "confidence": 0.9,
            "category": "water",
        })
    if stats.get("exercise_rate", 0) >= 0.6:
        insights.append({
            "pattern": f"Frequência de exercício: {int(stats['exercise_rate'] * 100)}% dos dias",
            "confidence": 0.87,
            "category": "exercise",
        })
    elif log_count >= 5:
        insights.append({
            "pattern": "Exercício abaixo da meta — menos da metade dos dias com atividade",
            "confidence": 0.84,
            "category": "exercise",
        })

    tuesday_issues = _count_tuesday_pattern(logs)
    if tuesday_issues >= 2:
        insights.append({
            "pattern": "Terças com sono baixo coincidem com menos exercício",
            "confidence": 0.91,
            "category": "sleep",
        })

    return insights


def _build_primary_action(
    stats: Dict[str, Any],
    current_metrics: Dict[str, Any],
    current_note: str,
    log_count: int,
) -> Dict[str, Any]:
    current_km = current_metrics.get("distance_km")
    current_water = current_metrics.get("water_liters")
    avg_km = stats.get("avg_distance_km")
    avg_water = stats.get("avg_water_l")
    avg_sleep = stats.get("avg_sleep_h")

    if log_count < 3:
        return {
            "category": "data",
            "direction": "increase",
            "icon": "📓",
            "title": "Registre mais hábitos",
            "action": "Faça check-ins diários por pelo menos uma semana",
            "reasoning": "Com mais registros o coach consegue comparar tendências e sugerir ações personalizadas.",
            "confidence": 0.95,
        }

    # Water — today's intake or recent average
    water_today = current_water if current_water is not None else stats.get("last_water_l")
    if water_today is not None and water_today < 1.8:
        target = 2.5 if water_today < 1.2 else 2.0
        return {
            "category": "water",
            "direction": "increase",
            "icon": "💧",
            "title": "Beba mais água",
            "action": f"Meta amanhã: {target} L de água (hoje/registro recente: {water_today} L)",
            "reasoning": (
                f"Sua média é {avg_water or water_today} L. "
                "Hidratação abaixo de 2 L pode afetar energia e recuperação."
            ),
            "confidence": 0.92,
        }

    # Recovery — overtraining vs average
    if current_km and avg_km and current_km >= avg_km * 1.45 and current_km >= 6:
        return {
            "category": "exercise",
            "direction": "decrease",
            "icon": "🧘",
            "title": "Reduza a intensidade",
            "action": f"Amanhã prefira recuperação ativa (~{round(avg_km, 1)} km leve ou alongamento)",
            "reasoning": (
                f"Hoje você fez {current_km} km, bem acima da média de {avg_km} km. "
                "Descanso evita lesão e sustenta progresso."
            ),
            "confidence": 0.89,
        }

    # Exercise gap — few recent workouts
    if stats.get("recent_exercise_days", 0) == 0 and log_count >= 3:
        return {
            "category": "exercise",
            "direction": "increase",
            "icon": "🏃",
            "title": "Retome o exercício",
            "action": "Amanhã: caminhada de 20 min ou corrida leve de 2–3 km",
            "reasoning": "Nenhum exercício nos últimos 5 registros. Recomeçar leve facilita consistência.",
            "confidence": 0.9,
        }

    # Run more — below average distance
    if current_km and avg_km and current_km < avg_km * 0.75:
        target = round(max(current_km + 0.5, avg_km), 1)
        return {
            "category": "exercise",
            "direction": "increase",
            "icon": "🏃",
            "title": "Corra um pouco mais",
            "action": f"Próxima corrida: {target} km (hoje {current_km} km · média {avg_km} km)",
            "reasoning": "Distância de hoje ficou abaixo do seu padrão recente — progressão gradual é segura.",
            "confidence": 0.88,
        }

    if not current_km and avg_km and stats.get("recent_exercise_days", 0) <= 1:
        target = round(avg_km, 1)
        return {
            "category": "exercise",
            "direction": "increase",
            "icon": "🏃",
            "title": "Volte a correr",
            "action": f"Meta: {target} km na próxima sessão (sua média recente)",
            "reasoning": "Seu histórico mostra capacidade para essa distância, mas exercício ficou irregular.",
            "confidence": 0.86,
        }

    # Sleep
    if avg_sleep and avg_sleep < 6.5:
        return {
            "category": "sleep",
            "direction": "increase",
            "icon": "😴",
            "title": "Durma mais",
            "action": "Meta: 7–8 h de sono nas próximas noites",
            "reasoning": f"Média de sono {avg_sleep} h — abaixo do ideal para recuperação e hábitos.",
            "confidence": 0.9,
        }

    # Water maintain high if doing well
    if water_today and water_today >= 2.5 and avg_water and avg_water >= 2.0:
        return {
            "category": "water",
            "direction": "maintain",
            "icon": "💧",
            "title": "Hidratação no caminho certo",
            "action": f"Mantenha ~{round(avg_water, 1)} L por dia",
            "reasoning": f"Excelente: hoje {water_today} L e média de {avg_water} L.",
            "confidence": 0.91,
        }

    # Default maintain with specifics
    if current_km and avg_km:
        return {
            "category": "exercise",
            "direction": "maintain",
            "icon": "✅",
            "title": "Mantenha o ritmo",
            "action": f"Continue com ~{round(avg_km, 1)} km por sessão",
            "reasoning": (
                f"Hoje {current_km} km está alinhado à média ({avg_km} km) "
                f"em {stats.get('distance_samples', 0)} corrida(s) analisada(s)."
            ),
            "confidence": 0.87,
        }

    if avg_water and avg_water >= 2.0:
        return {
            "category": "water",
            "direction": "maintain",
            "icon": "💧",
            "title": "Mantenha a hidratação",
            "action": f"Continue com ~{avg_water} L de água por dia",
            "reasoning": f"Boa consistência em {stats.get('water_samples', 0)} registro(s) de água.",
            "confidence": 0.85,
        }

    return {
        "category": "general",
        "direction": "maintain",
        "icon": "🌿",
        "title": "Continue registrando",
        "action": "Mantenha o hábito de check-in diário",
        "reasoning": f"{log_count} registros analisados — consistência ajuda o coach a refinar sugestões.",
        "confidence": 0.82,
    }


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
