"""Tests for HabitFlow Team orchestrator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.executors import execute_analyzer, execute_guardian, seed_demo_logs
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
    assert len(result["events"]) > 10
