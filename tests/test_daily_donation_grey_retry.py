"""A grey donation page returns immediately instead of burning the route wall."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = ((ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8") + (Path(__file__).resolve().parents[1] / "wjdr_daily_controller.py").read_text(encoding="utf-8") + (Path(__file__).resolve().parents[1] / "wjdr_runtime_config.py").read_text(encoding="utf-8"))
    start = source.index("def run_alliance_food_donation_plan")
    end = source.index("def run_free_hero_recruit_plan", start)
    route = source[start:end]
    classify = route[
        route.index("# Classify the two reviewed donation states concurrently.") :
        route.index("if stage:")
    ]

    assert "time.monotonic() + 3.0" in classify
    assert "food_streak >= 2" in classify
    assert "grey_streak >= 2" in classify
    assert "candidate_page = daily_alliance_donation_page_is_visible" in classify
    assert "未等待蓝色按钮、未再次长按，立即返回并继续后续任务" in classify
    assert "wait_for_gather_step(" not in classify
    assert "target.shell(" not in classify
    assert "assert image is not None" in route
    assert "联盟捐献关联路线已达到30秒总上限" in route
    print("daily donation grey retry fast return: PASS")


if __name__ == "__main__":
    main()
