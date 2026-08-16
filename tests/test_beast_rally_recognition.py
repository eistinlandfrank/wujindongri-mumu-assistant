from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from wjdr_backend import (
    BeastRallyState,
    beast_rally_new_busy_queue_indexes,
    match_beast_rally_active_panel,
    match_beast_rally_formation,
    match_beast_rally_stamina_more,
    match_beast_rally_open_button,
    match_beast_rally_progress_sidebar_collapsed,
    match_beast_rally_progress_wilderness_tab,
    match_beast_rally_selector,
    match_beast_rally_world_search,
    match_beast_rally_sheet,
    match_beast_rally_sheet_controls,
    read_beast_rally_dispatch_stamina,
    read_beast_rally_dispatch_stamina_shortfall,
    read_beast_rally_wilderness_queue_counts,
    read_beast_rally_wilderness_queue_states,
    read_beast_rally_selector_level,
)


ASSETS = Path("assets")


def paste_asset(
    frame: Image.Image,
    name: str,
    position: tuple[int, int],
) -> None:
    with Image.open(ASSETS / name) as asset:
        frame.paste(asset.convert("RGB"), position)


class BeastRallyRecognitionTests(unittest.TestCase):
    def test_full_wilderness_frame_exposes_only_search_lens(self):
        image = Image.new("RGB", (1440, 2560), (45, 76, 115))
        paste_asset(image, "beast_rally_world_search_dense_live.png", (25, 1682))
        paired = image.copy()
        paste_asset(paired, "beast_rally_world_town_dense_live.png", (1225, 2250))
        point, score = match_beast_rally_world_search(paired)
        self.assertIsNotNone(point, score)
        self.assertLess(point[0], round(image.width * 0.22))

    def test_round_world_search_requires_same_frame_dense_town_anchor(self):
        image = Image.new("RGB", (1440, 2560), (45, 76, 115))
        paste_asset(image, "beast_rally_world_search_round_live.png", (25, 1682))
        point, _score = match_beast_rally_world_search(image)
        self.assertIsNone(point)

        paired = image.copy()
        paste_asset(paired, "beast_rally_world_town_dense_live.png", (1225, 2250))
        point, score = match_beast_rally_world_search(paired)
        self.assertIsNotNone(point, score)
        self.assertEqual(point, (90, 1754))

    def test_round_world_search_does_not_authorise_city_or_old_search_alone(self):
        city = Image.new("RGB", (1440, 2560), (45, 76, 115))
        paste_asset(city, "daily_city_wilderness_entry.png", (1187, 2251))
        paste_asset(city, "beast_rally_world_search_round_live.png", (25, 1682))
        self.assertIsNone(match_beast_rally_world_search(city)[0])

        old_only = Image.new("RGB", (1440, 2560), (45, 76, 115))
        paste_asset(old_only, "beast_rally_world_search_dense_live.png", (25, 1682))
        self.assertIsNone(match_beast_rally_world_search(old_only)[0])

    def test_selector_requires_beast_and_blue_search_and_reads_level(self):
        image = Image.new("RGB", (1440, 2560), (36, 75, 110))
        paste_asset(image, "beast_rally_beast_target.png", (400, 1660))
        paste_asset(image, "beast_rally_level_field_8.png", (1075, 2020))
        paste_asset(image, "beast_rally_search_button.png", (430, 2310))
        self.assertIs(match_beast_rally_selector(image).state, BeastRallyState.SELECTOR)
        self.assertEqual(read_beast_rally_selector_level(image), 8)

        # Auto Join is present in the same screenshot, but the actionable
        # point must stay on the large central blue Search button.
        point = match_beast_rally_selector(image).point
        self.assertIsNotNone(point)
        self.assertLess(point[0], round(image.width * 0.80))

    def test_selector_uses_bottom_drawer_geometry_on_full_runtime_frame(self):
        image = Image.new("RGB", (1440, 2560), (36, 75, 110))
        beast = Image.open(Path("assets/beast_rally_beast_target.png")).convert("RGB")
        search = Image.open(Path("assets/beast_rally_search_button.png")).convert("RGB")
        level = Image.open(Path("assets/beast_rally_level_field_8.png")).convert("RGB")
        image.paste(beast, (400, 1660))
        image.paste(level, (1075, 2020))
        image.paste(search, (430, 2310))
        self.assertIs(match_beast_rally_selector(image).state, BeastRallyState.SELECTOR)
        self.assertEqual(read_beast_rally_selector_level(image), 8)

    def test_only_orange_rally_control_matches(self):
        image = Image.new("RGB", (1440, 2560), (35, 67, 104))
        button = Image.open(Path("assets/beast_rally_open_button_25.png")).convert("RGB")
        image.paste(button, (470, 1200))
        point, score = match_beast_rally_open_button(image)
        self.assertIsNotNone(point, score)

    def test_rally_sheet_requires_three_minutes_and_launch(self):
        image = Image.new("RGB", (1440, 2560), (126, 165, 211))
        paste_asset(image, "beast_rally_sheet_header.png", (527, 650))
        paste_asset(image, "beast_rally_three_minutes_selected.png", (125, 1080))
        paste_asset(image, "beast_rally_launch_button.png", (500, 1640))
        match = match_beast_rally_sheet(image)
        self.assertIs(match.state, BeastRallyState.RALLY_SHEET)
        self.assertGreater(match.score, 0.90)
        self.assertIs(
            match_beast_rally_sheet_controls(image).state,
            BeastRallyState.RALLY_SHEET,
        )

    def test_formation_requires_first_group_and_reads_final_cost_only(self):
        image = Image.new("RGB", (1440, 2560), (20, 65, 109))
        paste_asset(image, "beast_rally_formation_anchor.png", (105, 26))
        paste_asset(image, "beast_rally_first_formation_selected.png", (48, 151))
        with Image.open(
            Path("tests/fixtures/beast_rally_dispatch_cost_20_live.png")
        ) as cost:
            image.paste(cost.convert("RGB"), (875, 2360))
        # The tight live cost crop supplies the authoritative post-selection
        # digits. Re-paste the account-free reviewed title over only its top
        # title lane so the page proof and numeric proof stay independent.
        paste_asset(image, "beast_rally_dispatch_label.png", (925, 2360))
        match = match_beast_rally_formation(image)
        self.assertIs(match.state, BeastRallyState.FORMATION)
        self.assertIn("first", dict(match.anchors))
        self.assertEqual(read_beast_rally_dispatch_stamina(image), 20)

    def test_live_red_20_shortfall_and_stamina_use_page_are_exact(self):
        formation = Image.new("RGB", (1440, 2560), (20, 65, 109))
        paste_asset(formation, "beast_rally_formation_anchor.png", (105, 26))
        paste_asset(formation, "beast_rally_first_formation_selected.png", (48, 151))
        paste_asset(formation, "beast_rally_dispatch_label.png", (925, 2360))
        paste_asset(formation, "beast_rally_dispatch_stamina_red_20_live.png", (1085, 2425))
        self.assertEqual(read_beast_rally_dispatch_stamina_shortfall(formation), 20)
        self.assertIsNone(match_beast_rally_stamina_more(formation).point)

        stamina = Image.new("RGB", (1440, 2560), (190, 215, 236))
        paste_asset(stamina, "beast_rally_stamina_more_title_live.png", (575, 230))
        paste_asset(stamina, "beast_rally_stamina_restore10_live.png", (330, 1005))
        paste_asset(stamina, "beast_rally_stamina_use_label_live.png", (1080, 985))
        match = match_beast_rally_stamina_more(stamina)
        self.assertIs(match.state, BeastRallyState.STAMINA_MORE)
        self.assertEqual(match.point, (1162, 1035))
        # The yellow purchase control below must never become actionable.
        self.assertLess(match.point[1], 1150)

    def test_rallying_panel_is_passive(self):
        image = Image.new("RGB", (1440, 2560), (45, 76, 115))
        icon = Image.open(Path("assets/beast_rally_progress_icon.png")).convert("RGB")
        state = Image.open(Path("assets/beast_rally_state_rallying.png")).convert("RGB")
        image.paste(icon, (100, 500))
        image.paste(state, (100 + icon.width + 8, 500))
        match = match_beast_rally_active_panel(image)
        self.assertIs(match.state, BeastRallyState.RALLYING)
        self.assertIsNone(match.point)

    def test_collapsed_progress_sidebar_is_left_strip_only(self):
        image = Image.new("RGB", (1440, 2560), (45, 76, 115))
        arrow = Image.open(
            Path("assets/beast_rally_progress_sidebar_collapsed_live.png")
        ).convert("RGB")
        image.paste(arrow, (18, 1060))
        point, score = match_beast_rally_progress_sidebar_collapsed(image)
        self.assertIsNotNone(point, score)
        self.assertLess(point[0], 100)

    def test_current_collapsed_arrow_live_frames_accept_dual_context(self):
        fixtures = Path("tests/fixtures/beast_rally")
        for index in (1, 2):
            with self.subTest(index=index):
                with Image.open(fixtures / f"collapsed_round_world_live_{index}.png") as source:
                    frame = source.convert("RGB")
                point, score = match_beast_rally_progress_sidebar_collapsed(frame)
                self.assertEqual(point, (45, 1111), score)
                missing_world = frame.copy()
                missing_world.paste((36, 72, 109), (25, 1682, 156, 1826))
                # A transient Search-skin miss is now covered by the exact
                # same-frame Town + collapsed-arrow dual context.
                self.assertEqual(
                    match_beast_rally_progress_sidebar_collapsed(missing_world)[0],
                    (45, 1111),
                )
                missing_town = frame.copy()
                missing_town.paste((36, 72, 109), (1210, 2230, 1440, 2560))
                self.assertIsNone(
                    match_beast_rally_progress_sidebar_collapsed(missing_town)[0]
                )

    def test_current_collapsed_arrow_rejects_city_and_expanded_pages(self):
        fixture = Path("tests/fixtures/beast_rally/collapsed_round_world_live_2.png")
        with Image.open(fixture) as source:
            city = source.convert("RGB")
        paste_asset(city, "daily_city_wilderness_entry.png", (1180, 2240))
        self.assertIsNone(match_beast_rally_progress_sidebar_collapsed(city)[0])

        expanded = Image.new("RGB", (1440, 2560), (45, 76, 115))
        paste_asset(expanded, "beast_rally_progress_sidebar_expanded_live.png", (903, 1000))
        paste_asset(expanded, "beast_rally_world_search_round_live.png", (25, 1682))
        paste_asset(expanded, "beast_rally_world_town_dense_live.png", (1225, 2250))
        self.assertIsNone(match_beast_rally_progress_sidebar_collapsed(expanded)[0])

    def test_progress_wilderness_tab_is_expanded_panel_only(self):
        image = Image.new("RGB", (1440, 2560), (45, 76, 115))
        tab = Image.open(
            Path("assets/beast_rally_progress_wilderness_tab_live.png")
        ).convert("RGB")
        image.paste(tab, (455, 485))
        point, score = match_beast_rally_progress_wilderness_tab(image)
        self.assertIsNotNone(point, score)

    def test_expanded_wilderness_panel_counts_all_idle_queues(self):
        fixture = Image.new("RGB", (1440, 2560), (45, 76, 115))
        selected = Image.open(
            Path("assets/beast_rally_progress_wilderness_selected_live.png")
        ).convert("RGB")
        expanded = Image.open(
            Path("assets/beast_rally_progress_sidebar_expanded_live.png")
        ).convert("RGB")
        label = Image.open(
            Path("assets/beast_rally_progress_queue_label_live.png")
        ).convert("RGB")
        idle = Image.open(Path("assets/beast_rally_progress_idle_live.png")).convert("RGB")
        fixture.paste(selected, (455, 485))
        fixture.paste(expanded, (903, 1000))
        for index in range(6):
            y = 690 + index * 155
            fixture.paste(label, (350, y))
            fixture.paste(idle, (390, y + 80))
        self.assertEqual(
            read_beast_rally_wilderness_queue_counts(fixture),
            (6, 6),
        )
        self.assertEqual(
            read_beast_rally_wilderness_queue_states(fixture),
            (True, True, True, True, True, True),
        )

        # A busy row may replace its blue flag with a green state icon, but
        # the fixed row title remains.  Total rows must therefore come from
        # titles, not from the changing icon.
        busy_fixture = fixture.copy()
        busy_fixture.paste((45, 76, 115), (390, 690 + 5 * 155 + 80, 520, 690 + 5 * 155 + 140))
        self.assertEqual(
            read_beast_rally_wilderness_queue_counts(busy_fixture),
            (6, 5),
        )
        self.assertEqual(
            read_beast_rally_wilderness_queue_states(busy_fixture),
            (True, True, True, True, True, False),
        )

    def test_only_new_idle_to_busy_row_is_correlated_to_dispatch(self):
        self.assertEqual(
            beast_rally_new_busy_queue_indexes(
                (False, True, True, False, True, True),
                (False, True, False, False, True, True),
            ),
            (2,),
        )
        self.assertEqual(
            beast_rally_new_busy_queue_indexes((True, True), (False, False)),
            (0, 1),
        )



if __name__ == "__main__":
    unittest.main()
