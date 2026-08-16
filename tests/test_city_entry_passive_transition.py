"""The post-city-entry frame must wait passively, never tap twice."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    passive = "city_entry_tapped and time.monotonic() < transition_deadline"
    passive_at = source.index(passive)
    start = source.rfind("if page.state is DailyTaskState.CITY_ENTRY:", 0, passive_at)
    branch = source[start : source.index("actionable = (DailyTaskState.CLAIM_READY", passive_at)]
    terminal = "if city_entry_tapped or not city_point:"
    tap = "target.tap(*city_point)"
    assert passive in branch
    assert branch.index(passive) < branch.index(terminal) < branch.index(tap)
    assert branch.count(tap) == 1
    assert "不重复输入" in branch


if __name__ == "__main__":
    main()
    print("city entry passive transition focused checks: PASS")
