from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("if not run_free_hero_recruit_plan():")
    end = source.index("set_state(\"英雄免费招募路线未完整确认", start)
    recovery = source[start:end]

    assert recovery.count("target.screenshot()") == 2
    assert recovery.count("match_daily_city_entry(") == 2
    assert "stable(failure_city, verify_city)" in recovery
    assert recovery.index("stable(failure_city, verify_city)") < recovery.index("target.tap(*verify_city)")
    assert "hero_recruit_unavailable = True" in recovery
    assert "本进程仅跳过英雄并继续后续任务" in recovery
    assert "restart_daily_list_scan()" in recovery
    print("failed hero navigation yields to later tasks: PASS")


if __name__ == "__main__":
    main()
