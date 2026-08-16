"""Alliance donation uses one bounded segment when no coin reader exists."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
    start = source.index("def run_alliance_food_donation_plan")
    end = source.index("def run_free_hero_recruit_plan", start)
    route = source[start:end]

    assert "match_daily_alliance_food_donation(image, threshold)" in route
    assert '"input",\n                            "swipe",' in route
    assert route.count('"1200",') == 1
    assert '"10000",' not in route
    assert "str(food_point[0])" in route and "str(food_point[1])" in route
    assert "timeout=3" in route
    assert "target.tap(*food_point)" not in route
    assert "donation_route_deadline = time.monotonic() + min(" in route
    assert "AUTOMATION_STEP_TIMEOUT_SECONDS" in route
    assert "DAILY_RETRY_LOCK_MAX_SECONDS" in route
    assert "deadline = donation_route_deadline" in route
    assert "for _post_index in range(2):" in route
    assert "adaptive_operation_wait" not in route[route.index("for _post_index in range(2):"):route.index("if disabled_streak >= 2")]
    assert "post_blue_streak = post_blue_streak + 1 if candidate_food else 0" in route
    assert "disabled_streak = disabled_streak + 1 if disabled else 0" in route
    assert "disabled_streak >= 2" in route
    assert "post_blue_streak >= 2" in route
    assert "candidate_food is None" in route
    assert "daily_alliance_donation_page_is_visible(candidate, threshold)" in route
    assert "alliance_donation_window_clicks = DAILY_DONATION_WINDOW_CAP" in route
    assert "当前没有可靠联盟币数值读取器" in route
    assert "本轮不允许第二段" in route
    assert "不按时长推断次数，具体增长由每日任务页复核" in route
    assert "黄色钻石" in route
    print("daily donation short segmented hold: PASS")


if __name__ == "__main__":
    main()
