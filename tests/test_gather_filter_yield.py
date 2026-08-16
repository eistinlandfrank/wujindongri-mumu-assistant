from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("def yield_gather_selector_stage(")
    end = source.index("def recover_gather_world_from_task_hub", start)
    helper = source[start:end]

    proof = "all(daily_gather_selector_is_valid(image) for image in frames)"
    back = 'target.shell(["input", "keyevent", "4"])'
    defer = "defer_gather_kind(kind, DAILY_RETRY_LOCK_MAX_SECONDS)"
    reopen = "reopen_daily_tasks_from_gather_world"
    assert helper.index(proof) < helper.index(back) < helper.index(defer) < helper.index(reopen)
    assert "未点击搜索、地图、节点或出征" in helper
    assert "后页面未知；未作恢复输入" in helper

    gather_start = source.index("def run_gather_plan")
    gather_end = source.index("def run_shield_training_plan", gather_start)
    gather = source[gather_start:gather_end]
    assert gather.count("return yield_gather_selector_stage(") == 2
    assert "采集未确认仅满资源筛选状态" in gather
    assert "采集未确认满资源筛选已切换" in gather
    print("gather filter failure yields to later tasks: PASS")


if __name__ == "__main__":
    main()
