"""A donation hold is complete, double-framed, and cannot chain blindly."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = ((ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8") + (Path(__file__).resolve().parents[1] / "wjdr_daily_controller.py").read_text(encoding="utf-8") + (Path(__file__).resolve().parents[1] / "wjdr_runtime_config.py").read_text(encoding="utf-8"))
    start = source.index("def run_alliance_food_donation_plan")
    end = source.index("def run_free_hero_recruit_plan", start)
    route = source[start:end]

    # The common step helper is a two-fresh-frame stable-point gate and the
    # donation stage uses the exact blue-food/diamond-sibling recogniser.
    helper_start = source.index("def wait_for_gather_step")
    helper_end = source.index("def wait_for_gather_selector", helper_start)
    helper = source[helper_start:helper_end]
    assert "streak >= 2 and point" in helper
    assert "match_daily_alliance_food_donation(" in route

    # Exactly one reviewed ten-second hold exists; no short partial segment
    # may prematurely exit the donation window.
    assert route.count('"10000",') == 1
    assert '"1200",' not in route
    assert "timeout=12" in route
    assert "for _post_index in range(2):" in route
    segment = route[
        route.index("donation_route_deadline =") :
        route.index("if post_image is not None:")
    ]
    assert segment.count("target.shell(") == 1
    assert "adaptive_operation_wait" not in segment

    # Both route and retry ceilings are no greater than 30 seconds.  A blue
    # post-state explicitly forbids a second hold; only grey can mark the
    # current ordinary-donation window exhausted.
    assert "AUTOMATION_STEP_TIMEOUT_SECONDS" in segment
    assert "DAILY_RETRY_LOCK_MAX_SECONDS" in segment
    assert "deadline = donation_route_deadline" in route
    assert "联盟捐献关联路线已达到30秒总上限" in route
    assert "post_blue_streak >= 2" in segment
    assert "本轮不允许第二次长按" in segment
    assert "disabled_streak >= 2" in segment
    assert "alliance_donation_window_clicks = DAILY_DONATION_WINDOW_CAP" in segment
    assert "具体增长由每日任务页复核" in segment
    assert "diamond_point" not in route
    print("daily donation complete hold: PASS")


if __name__ == "__main__":
    main()
