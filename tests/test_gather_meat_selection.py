"""Regression for an overview round-trip that resets the selector to Beast."""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wjdr_backend import (  # noqa: E402
    daily_gather_meat_is_selected,
    daily_gather_selector_is_valid,
    match_daily_gather_meat_visible_tab,
)


def main() -> None:
    milestone = ROOT / "evidence" / "milestone-34-gather-resource-preselection-v501"
    for name in ("preselection-stop-private.png", "preselection-stop-2-private.png"):
        beast = Image.open(milestone / name).convert("RGB")
        assert daily_gather_selector_is_valid(beast)
        assert not daily_gather_meat_is_selected(beast, 0.90)
        point, score = match_daily_gather_meat_visible_tab(beast, 0.90)
        assert point is not None and 1330 <= point[0] <= 1380 and 1810 <= point[1] <= 1880
        assert score >= 0.99

    selected = Image.open(
        ROOT / "evidence" / "milestone-21-multi-march-capacity" / "16384-meat-selector-private-2.png"
    ).convert("RGB")
    assert daily_gather_selector_is_valid(selected)
    assert daily_gather_meat_is_selected(selected, 0.90)
    assert match_daily_gather_meat_visible_tab(selected, 0.90)[0] is None

    selected_right_root = ROOT / "evidence" / "milestone-35-meat-selected-right-v502"
    for name in ("selected-right-1-private.png", "selected-right-2-private.png"):
        selected_right = Image.open(selected_right_root / name).convert("RGB")
        assert daily_gather_selector_is_valid(selected_right)
        assert daily_gather_meat_is_selected(selected_right, 0.90)
        assert match_daily_gather_meat_visible_tab(selected_right, 0.90)[0] is None

    controller = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    assert "资源筛选页右侧生肉标签" in controller
    assert "生肉资源标签选中状态" in controller
    assert "未双帧确认中央生肉选中态；未点击搜索" in controller

    print("gather meat selector recovery: PASS")


if __name__ == "__main__":
    main()
