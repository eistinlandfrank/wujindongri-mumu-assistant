from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("if tutorial_camp_clicked:")
    end = source.index("self._log_for_device(target.device, f\"{label}任务未确认蓝色普通训练面板", start)
    completion = source[start:end]

    assert "match_daily_city_entry" in completion
    assert "target.tap(*city_point)" in completion
    assert "failed_training_kinds.add" not in completion
    assert "deferred_auxiliary_training.add" not in completion
    assert "不写入训练失败或等待锁" in completion
    assert "只由刷新后的精确进度卡决定是否开始下一批" in completion
    print("completed training tutorial continues from fresh Daily card: PASS")


if __name__ == "__main__":
    main()
