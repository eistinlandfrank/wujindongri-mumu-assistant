from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wjdr_backend import content_frame_mean_change


SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def test_stable_page_comparison_is_passive_and_resolution_safe() -> None:
    first = Image.new("RGB", (1440, 2560), "#153454")
    second = first.copy()
    assert content_frame_mean_change(first, second) == 0.0
    draw = ImageDraw.Draw(second)
    draw.rectangle((400, 600, 1000, 1800), fill="#f7f7f7")
    assert content_frame_mean_change(first, second) > 5.0
    assert content_frame_mean_change(first, Image.new("RGB", (720, 1280))) == float("inf")


def test_unknown_recovery_is_classified_and_has_no_generic_input() -> None:
    blocked = SOURCE.index("if blocked_state is not None and page.state is blocked_state:")
    reward = SOURCE.index("if page.state is DailyTaskState.REWARD_RESULT_READY:", blocked)
    unknown = SOURCE.index("if page.state is DailyTaskState.UNKNOWN:", reward)
    end = SOURCE.index("if page.state is DailyTaskState.CITY_ENTRY:", unknown)
    block = SOURCE[unknown:end]
    assert blocked < unknown < end
    assert "diagnose_daily_abnormal_exit(image, threshold)" in block
    assert "observe_abnormal_exit(" in block
    assert "DailyAbnormalExitKind.REWARD_TAP_ANYWHERE" in block
    assert "DailyAbnormalExitKind.DAILY_CLOSE_X" in block
    assert "DailyAbnormalExitKind.INTEL_MAP_BACK" in block
    assert "DailyAbnormalExitKind.WORLD_TOWN" in block
    assert "DailyAbnormalExitKind.NETWORK_WAIT" in block
    assert "DailyAbnormalExitKind.PAID_STOP" in block
    assert 'target.shell(["input", "keyevent", "4"])' not in block
    assert "safe_corner" not in block
    assert "未执行通用返回、左上角或页面中心点击" in block


if __name__ == "__main__":
    test_stable_page_comparison_is_passive_and_resolution_safe()
    test_unknown_recovery_is_classified_and_has_no_generic_input()
    print("bounded unknown recovery regression checks passed")
