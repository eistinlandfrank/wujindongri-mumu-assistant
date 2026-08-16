from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wjdr_backend import (
    DailyAbnormalExitKind,
    DailyTaskState,
    detect_daily_task_state,
    diagnose_daily_abnormal_exit,
)


SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
EVIDENCE = (
    ROOT
    / "evidence"
    / "milestone-72-correlated-claim-settlement"
    / "stopped-full-safe.png"
)


def test_live_late_reward_sheet_is_exact_reviewed_result() -> None:
    image = Image.open(EVIDENCE)
    result = detect_daily_task_state(image, 0.90)
    assert result.state is DailyTaskState.REWARD_RESULT_READY
    assert result.score >= 0.95
    abnormal = diagnose_daily_abnormal_exit(image, 0.90)
    assert abnormal.kind is DailyAbnormalExitKind.REWARD_TAP_ANYWHERE
    assert abnormal.point == (96, 1500)
    assert {name for name, _point in abnormal.anchors} == {
        "daily_tap_anywhere_exit_text",
    }


def test_exact_exit_text_keeps_a_bounded_multi_sheet_exit() -> None:
    assert SOURCE.count("recent_claim_result_deadline = time.monotonic() + 12.0") >= 4
    assert "late_correlated_claim = bool(" not in SOURCE
    assert "if not pending_claim and not late_correlated_claim:" not in SOURCE
    assert "claim_result_exit_cap = 4" in SOURCE
    assert "claim_result_exit_count += 1" in SOURCE
    assert "diagnose_daily_abnormal_exit(image, threshold)" in SOURCE
    assert "DailyAbnormalExitKind.REWARD_TAP_ANYWHERE" in SOURCE
    assert "双图OCR确认异常页显示点击任意位置退出" in SOURCE
    assert "已点击侧边空白点" in SOURCE
    assert "保留12秒只用于同一次领取的连续奖励页" in SOURCE
    assert "同链连续奖励页正在转场：保持被动多图分类" in SOURCE
    assert "claim_result_exit_count = 0" in SOURCE


if __name__ == "__main__":
    test_live_late_reward_sheet_is_exact_reviewed_result()
    test_exact_exit_text_keeps_a_bounded_multi_sheet_exit()
    print("late claim result regression checks passed")
