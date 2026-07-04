"""HabitFlow orchestrator — coordinator delegates cards via A2A + MCP."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mcp_server.store import (
    activity_log,
    board_get,
    card_assign,
    card_create,
    card_move,
    card_set_result,
    init_db,
    reset_board,
    route_card,
)
from runtime.executors import run_specialist, seed_demo_logs

# Pipeline templates
CHECKIN_PIPELINE = [
    {"title": "Coletar check-in do usuário", "labels": ["collect"], "points": 1},
    {"title": "Extrair métricas do texto livre", "labels": ["extract"], "points": 2},
    {"title": "Persistir histórico de hábitos", "labels": ["persist"], "points": 1},
]

ANALYSIS_PIPELINE = [
    {"title": "Buscar padrões históricos (RAG)", "labels": ["patterns"], "points": 3},
    {"title": "Gerar insights e sugestões", "labels": ["coach"], "points": 3},
    {"title": "Validar guardrails de saúde", "labels": ["safety"], "points": 2},
    {"title": "Entregar feedback ao usuário", "labels": ["notify"], "points": 1},
]

FULL_PIPELINE = CHECKIN_PIPELINE + ANALYSIS_PIPELINE


class HabitOrchestrator:
    def __init__(self) -> None:
        init_db()

    def run_sprint(
        self,
        user_input: str,
        user_id: str = "demo-user",
        mode: str = "auto",
    ) -> Dict[str, Any]:
        reset_board()
        if mode == "analysis" or "análise" in user_input.lower() or "semana" in user_input.lower():
            pipeline = ANALYSIS_PIPELINE
            seed_demo_logs(user_id)
        elif mode == "checkin":
            pipeline = CHECKIN_PIPELINE
        else:
            pipeline = FULL_PIPELINE
            if "análise" not in user_input.lower():
                seed_demo_logs(user_id)

        events: List[Dict[str, Any]] = []
        context: Dict[str, Any] = {
            "user_id": user_id,
            "user_input": user_input,
            "note": user_input,
            "entries": _parse_entries(user_input),
            "timestamp": datetime.utcnow().isoformat(),
            "mood_emoji": "💪",
            "insights": [],
            "suggestions": [],
        }

        def emit(channel: str, **kwargs: Any) -> None:
            events.append({"channel": channel, "timestamp": datetime.utcnow().isoformat(), **kwargs})

        emit("a2a", from_="user", to="coordinator", kind="sprint.start",
             text=f"Inicia pipeline com: {user_input[:60]}...")

        cards: List[Dict[str, Any]] = []
        for spec in pipeline:
            created = card_create("coordinator", spec["title"], spec["labels"], user_input, spec["points"])
            cards.append(created)
            emit("mcp", from_="coordinator", kind="card.create", cardId=created["cardId"],
                 text=f'card.create → "{spec["title"]}"')

        coach_result: Optional[Dict[str, Any]] = None
        guardian_result: Optional[Dict[str, Any]] = None

        for card in cards:
            card_id = card["cardId"]
            labels = card["labels"]
            assignee = route_card(labels)

            emit("a2a", from_="coordinator", to=assignee, kind="task.delegate",
                 cardId=card_id, text=f"delega {card_id} ({','.join(labels)}) → {assignee}")
            card_assign("coordinator", card_id, assignee)
            emit("mcp", from_="coordinator", kind="card.assign", cardId=card_id,
                 text=f"card.assign {card_id} → {assignee}")
            card_move("coordinator", card_id, "todo")
            emit("mcp", from_="coordinator", kind="card.move", cardId=card_id, text=f"card.move → todo")

            emit("a2a", from_=assignee, to="coordinator", kind="task.accepted", cardId=card_id,
                 text=f"{assignee} aceitou {card_id}")
            card_move(assignee, card_id, "in_progress")
            emit("mcp", from_=assignee, kind="card.move", cardId=card_id, text="card.move → in_progress")

            payload = _build_payload(assignee, context)
            result = run_specialist(assignee, payload)
            card_set_result(card_id, assignee, result)
            activity_log(assignee, "executed", card_id, {"executedBy": assignee})
            emit("exec", from_=assignee, kind="executed", cardId=card_id,
                 text=f"{assignee} executou {card_id}", result=result)
            emit("mcp", from_=assignee, kind="activity.log", cardId=card_id,
                 text=f'activity.log executedBy={assignee}')

            _merge_context(context, assignee, result)
            if assignee == "coach-agent":
                coach_result = result
            if assignee == "guardian-agent":
                guardian_result = result

            emit("a2a", from_=assignee, to="coordinator", kind="task.completed", cardId=card_id,
                 text=f"{card_id} concluído")
            card_move(assignee, card_id, "review")
            emit("mcp", from_=assignee, kind="card.move", cardId=card_id, text="card.move → review")

            if assignee == "guardian-agent" and not result.get("approved", True):
                emit("a2a", from_="guardian-agent", to="coordinator", kind="review.verdict",
                     cardId=card_id, text="Guardian: BLOCKED", verdict="fail")
            else:
                emit("a2a", from_="coordinator", to="coordinator", kind="review.verdict",
                     cardId=card_id, text="PASS ✔", verdict="pass")

            card_move("coordinator", card_id, "done")
            emit("mcp", from_="coordinator", kind="card.move", cardId=card_id, text="card.move → done")

        emit("a2a", from_="coordinator", to="user", kind="sprint.report",
             text="Pipeline concluído — todos os cards em Done")

        return {
            "sprint_id": str(uuid4()),
            "user_id": user_id,
            "events": events,
            "board": board_get(),
            "final_message": context.get("final_message") or _build_final_message(context),
            "coach_result": coach_result,
            "guardian_result": guardian_result,
        }


def _parse_entries(user_input: str) -> List[Dict[str, Any]]:
    entries = []
    lower = user_input.lower()
    if re_search_any(lower, ["corri", "km", "exerc", "caminh"]):
        entries.append({"habit_id": "exercise", "value": True, "note": user_input})
    if re_search_any(lower, ["água", "agua", "litro", "bebi"]):
        entries.append({"habit_id": "water", "value": True, "note": user_input})
    if re_search_any(lower, ["dormi", "sono", "h de sono"]):
        entries.append({"habit_id": "sleep", "value": True, "note": user_input})
    if not entries:
        entries.append({"habit_id": "general", "value": True, "note": user_input})
    return entries


def re_search_any(text: str, keywords: List[str]) -> bool:
    return any(k in text for k in keywords)


def _build_payload(agent_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    if agent_id == "collector-agent":
        return {
            "user_id": ctx["user_id"],
            "entries": ctx["entries"],
            "mood_emoji": ctx.get("mood_emoji"),
            "timestamp": ctx["timestamp"],
        }
    if agent_id == "analyzer-agent":
        note = ctx.get("note", "")
        habit = ctx["entries"][0]["habit_id"] if ctx["entries"] else "general"
        return {"note": note, "habit_id": habit}
    if agent_id == "coach-agent":
        return {
            "user_id": ctx["user_id"],
            "current_metrics": ctx.get("metrics", {}),
            "current_note": ctx.get("note", ""),
        }
    if agent_id == "guardian-agent":
        return {
            "suggestions": ctx.get("suggestions", []),
            "user_notes": ctx.get("note", ""),
        }
    if agent_id == "notifier-agent":
        return {
            "insights": ctx.get("insights", []),
            "suggestions": ctx.get("suggestions", []),
            "primary_action": ctx.get("primary_action"),
        }
    return ctx


def _merge_context(ctx: Dict[str, Any], agent_id: str, result: Dict[str, Any]) -> None:
    if agent_id == "analyzer-agent":
        ctx["metrics"] = result.get("metrics", {})
    if agent_id == "coach-agent":
        ctx["insights"] = result.get("insights", [])
        ctx["suggestions"] = result.get("suggestions", [])
        ctx["primary_action"] = result.get("primary_action")
    if agent_id == "notifier-agent":
        ctx["final_message"] = result.get("message", "")


def _build_final_message(ctx: Dict[str, Any]) -> str:
    if ctx.get("final_message"):
        return ctx["final_message"]
    metrics = ctx.get("metrics", {})
    if metrics:
        return f"Check-in registrado. Métricas: {json.dumps(metrics, ensure_ascii=False)}"
    return "Pipeline executado com sucesso."
