"""A missing resource node yields to later Daily items without map taps."""

from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import daily_gather_march_is_active, daily_gather_selector_is_valid


def test_live_timeout_frames_are_safe_selector_without_active_march() -> None:
    evidence = ROOT / "evidence" / "milestone-41-gather-search-yield-v508"
    for name in ("search_timeout_1-private.png", "search_timeout_2-private.png"):
        frame = Image.open(evidence / name)
        assert daily_gather_selector_is_valid(frame)
        assert not daily_gather_march_is_active(frame, 0.94)


def test_timeout_recovery_is_selector_only_and_defers_one_kind() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    helper = source.split("def yield_gather_search_timeout", 1)[1].split(
        "def yield_gather_selector_stage", 1
    )[0]
    assert helper.count("daily_gather_selector_is_valid") == 1
    assert 'target.shell(["input", "keyevent", "4"])' in helper
    assert "defer_gather_kind(kind, DAILY_RETRY_LOCK_MAX_SECONDS)" in helper
    assert "reopen_daily_tasks_from_gather_world" in helper
    assert "target.tap" not in helper
    assert "不点击地图或节点" in helper

    gather_plan = source.split("def run_gather_plan", 1)[1].split(
        "def set_daily_training_quantity_to_max", 1
    )[0]
    assert "return yield_gather_search_timeout(kind, label)" in gather_plan
    assert "deferred_gather_recheck_at.get(item.kind, 0.0)" in source

    verify_block = source.split(
        "verify_missions = tuple(", 1
    )[1].split("same_plan =", 1)[0]
    assert "match_daily_gather_missions" in verify_block
    assert "item.kind not in dispatched_gather_kinds" in verify_block
    assert "deferred_gather_recheck_at.get(item.kind, 0.0)" in verify_block
    mismatch = source.split("if not same_plan:", 1)[1].split("first =", 1)[0]
    assert "restart_daily_list_scan()" in mismatch
    assert "continue" in mismatch
    assert "break" not in mismatch


def main() -> None:
    test_live_timeout_frames_are_safe_selector_without_active_march()
    test_timeout_recovery_is_selector_only_and_defers_one_kind()
    print("gather search yield regression checks passed")


if __name__ == "__main__":
    main()
