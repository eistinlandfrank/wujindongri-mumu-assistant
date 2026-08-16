"""Account-scoped five-minute free-recruit scheduling regression."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")


def test_free_recruit_uses_persisted_five_minute_deadline() -> None:
    assert "DAILY_HERO_FREE_RECRUIT_RETRY_SECONDS = 5 * 60" in SOURCE
    assert 'f"daily_hero_recruit_{donation_identity}.json"' in SOURCE
    assert "defer_hero_recruit()" in SOURCE
    assert "hero_recruit_is_deferred()" in SOURCE


def test_cooldown_is_checked_only_at_daily_mission_boundary() -> None:
    mission = SOURCE.index("hero_mission = (")
    scan_tail = SOURCE[mission : mission + 500]
    assert "if hero_recruit_is_deferred()" in scan_tail
    assert "match_daily_hero_recruit_mission" in scan_tail
    helper = SOURCE[
        SOURCE.index("def hero_recruit_is_deferred") : SOURCE.index(
            "training_route_attempted", SOURCE.index("def hero_recruit_is_deferred")
        )
    ]
    assert "target.tap" not in helper
    assert "target.shell" not in helper


if __name__ == "__main__":
    test_free_recruit_uses_persisted_five_minute_deadline()
    test_cooldown_is_checked_only_at_daily_mission_boundary()
    print("hero free recruit cooldown: PASS")
