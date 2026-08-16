"""A fixed-camp second entry must yield immediately to an existing queue."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    finish_start = source.index("def finish_training_camp_double_enter")
    finish_end = source.index("def run_shield_training_plan", finish_start)
    finish = source[finish_start:finish_end]

    assert "kind: DailyMissionKind" in finish
    assert "match_daily_training_active(" in finish
    assert "if active_streak >= 2:" in finish
    assert "defer_active_training_and_reopen_daily(label, kind)" in finish
    assert 'return "active_queue"' in finish
    assert "立即保留队列并返回每日任务" in finish
    assert "speed" not in finish.lower()
    assert "diamond" not in finish.lower()

    shield_start = finish_end
    shield_end = source.index("def run_auxiliary_training_plan", shield_start)
    shield = source[shield_start:shield_end]
    assert 'if double_enter_result == "active_queue":\n                        return True' in shield
    assert 'if double_enter_result != "normal_panel":' in shield

    auxiliary_start = shield_end
    auxiliary_end = source.index("def run_daily_building_upgrade_plan", auxiliary_start)
    auxiliary = source[auxiliary_start:auxiliary_end]
    assert 'if double_enter_result == "active_queue":\n                        return True' in auxiliary
    assert 'if double_enter_result != "normal_panel":' in auxiliary


if __name__ == "__main__":
    main()
    print("training active queue double entry: PASS")
