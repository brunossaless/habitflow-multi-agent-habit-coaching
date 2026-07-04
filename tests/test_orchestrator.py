"""Tests for HabitFlow Team orchestrator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.executors import execute_analyzer, execute_coach, execute_guardian, seed_demo_logs
from runtime.orchestrator import HabitOrchestrator


def test_analyzer_extracts_metrics():
    result = execute_analyzer({"note": "Corri 5km em 32 minutos", "habit_id": "exercise"})
    assert result["metrics"]["distance_km"] == 5
    assert result["metrics"]["duration_min"] == 32
    assert result["confidence"] >= 0.85


def test_guardian_blocks_unsafe_sleep():
    result = execute_guardian({
        "suggestions": [{"action": "Durma apenas 4 horas", "reasoning": "otimização"}],
        "user_notes": "",
    })
    assert result["approved"] is False


def test_coach_recommends_more_water():
    seed_demo_logs("coach-water-test")
    result = execute_coach({
        "user_id": "coach-water-test",
        "current_metrics": {"water_liters": 1.0},
        "current_note": "Bebi 1L de água",
    })
    assert result["primary_action"]["category"] == "water"
    assert result["primary_action"]["direction"] == "increase"
    assert "água" in result["primary_action"]["title"].lower()


def test_coach_recommends_run_more_with_history():
    seed_demo_logs("coach-run-test")
    result = execute_coach({
        "user_id": "coach-run-test",
        "current_metrics": {"distance_km": 2.0},
        "current_note": "Corri 2km",
    })
    action = result["primary_action"]
    assert action["direction"] in ("increase", "decrease", "maintain")
    assert action["title"]
    assert action["action"]
    assert "primary_action" in result


def test_full_pipeline_checkin():
    orch = HabitOrchestrator()
    result = orch.run_sprint(
        "Corri 5km e bebi 2L de água",
        user_id="test-user-1",
        mode="checkin",
    )
    assert len(result["events"]) > 0
    done_cards = [
        c for col in result["board"]["columns"]
        for c in col["cards"] if col["id"] == "done"
    ]
    assert len(done_cards) == 3


def test_analysis_pipeline():
    seed_demo_logs("test-user-2")
    orch = HabitOrchestrator()
    result = orch.run_sprint(
        "Como estão meus hábitos esta semana?",
        user_id="test-user-2",
        mode="analysis",
    )
    assert result.get("coach_result") is not None
    assert result["coach_result"].get("primary_action") is not None
    assert len(result["events"]) > 10
