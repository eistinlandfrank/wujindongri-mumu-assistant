"""Fixed camp points stay inside an exact troop-Go/city-proof lineage."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")

    helper_start = source.index("def reviewed_fixed_training_camp_point")
    helper_end = source.index("def finish_training_camp_double_enter", helper_start)
    fixed_helper = source[helper_start:helper_end]
    assert "DailyMissionKind.TRAIN_SHIELD: (720, 1200)" in fixed_helper
    assert "DailyMissionKind.TRAIN_SPEAR: (720, 1095)" in fixed_helper
    assert "DailyMissionKind.TRAIN_ARCHER: (720, 1130)" in fixed_helper
    assert "map_content_point(reference, (1440, 2560), screenshot)" in fixed_helper

    finish_start = helper_end
    finish_end = source.index("def run_shield_training_plan", finish_start)
    finish = source[finish_start:finish_end]
    assert "require_ordinary_entry: bool = False" in finish
    assert "panel_streak >= 2 and (entry_tapped or not require_ordinary_entry)" in finish
    assert "entry_streak >= 2 and entry_point and not entry_tapped" in finish

    shield_start = finish_end
    shield_end = source.index("def run_auxiliary_training_plan", shield_start)
    shield = source[shield_start:shield_end]
    shield_city_gate = shield.index("if city_streak >= 2:")
    shield_fixed_point = shield.index("reviewed_fixed_training_camp_point(")
    assert shield_city_gate < shield_fixed_point
    assert 'return "reviewed_city_camp"' in shield[shield_fixed_point:]
    assert 'require_ordinary_entry=transition_kind == "reviewed_city_camp"' in shield

    auxiliary_start = shield_end
    auxiliary_end = source.index("def run_daily_building_upgrade_plan", auxiliary_start)
    auxiliary = source[auxiliary_start:auxiliary_end]
    auxiliary_city_gate = auxiliary.index("if city_streak >= 2:")
    auxiliary_fixed_point = auxiliary.index("reviewed_fixed_training_camp_point(kind, image)")
    assert auxiliary_city_gate < auxiliary_fixed_point
    assert 'return "reviewed_city_camp"' in auxiliary[auxiliary_fixed_point:]
    assert 'require_ordinary_entry=transition_kind == "reviewed_city_camp"' in auxiliary

    # The fixed helper has exactly two call sites: Shield and the kind-bound
    # Spear/Archer transition.  It is not available to startup recovery or
    # unrelated page families.
    assert source.count("reviewed_fixed_training_camp_point(") == 3

    shield_card_start = source.index("if shield_mission:")
    shield_card_end = source.index("auxiliary_training = next(", shield_card_start)
    shield_card = source[shield_card_start:shield_card_end]
    assert shield_card.index("target.tap(*verified_shield.go_point)") < shield_card.index(
        "run_shield_training_plan()"
    )

    auxiliary_card_start = source.index("if auxiliary_training:")
    auxiliary_card_end = source.index("missions = match_daily_gather_missions", auxiliary_card_start)
    auxiliary_card = source[auxiliary_card_start:auxiliary_card_end]
    assert auxiliary_card.index("target.tap(*verified_auxiliary.go_point)") < auxiliary_card.index(
        "run_auxiliary_training_plan(verified_auxiliary.kind)"
    )


if __name__ == "__main__":
    main()
    print("training fixed camp fallback: PASS")
