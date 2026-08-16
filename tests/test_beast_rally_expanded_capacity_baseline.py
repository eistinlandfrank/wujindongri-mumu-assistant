from pathlib import Path
import sys
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wjdr_backend import (
    BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ASSET,
    BUILTIN_BEAST_RALLY_WORLD_TOWN_DENSE_ASSET,
    DailyMarchCapacity,
    beast_rally_expanded_capacity_baseline,
    match_beast_rally_world_search,
)


ROOT = Path(__file__).resolve().parents[1]


def paste_centre(frame: Image.Image, asset: str, centre: tuple[int, int]) -> None:
    patch = Image.open(ROOT / asset).convert("RGB")
    frame.paste(patch, (centre[0] - patch.width // 2, centre[1] - patch.height // 2))


def cap(used: int, total: int) -> DailyMarchCapacity:
    return DailyMarchCapacity(used=used, total=total, confidence=0.99)


class ExpandedCapacityBaselineTests(unittest.TestCase):
    def test_all_idle_expanded_panel_becomes_capacity_baseline(self):
        self.assertEqual(
            beast_rally_expanded_capacity_baseline((True,) * 6, None, None),
            (0, 6),
        )

    def test_busy_target_title_may_hide_one_account_row(self):
        self.assertEqual(
            beast_rally_expanded_capacity_baseline(
                (True,) * 5, cap(1, 6), cap(1, 6)
            ),
            (1, 6),
        )

    def test_disagreement_or_allied_extra_row_fails_closed(self):
        self.assertIsNone(
            beast_rally_expanded_capacity_baseline(
                (True,) * 5, cap(1, 6), cap(2, 6)
            )
        )
        self.assertIsNone(
            beast_rally_expanded_capacity_baseline(
                (True,) * 6, cap(1, 6), cap(1, 6)
            )
        )
        self.assertIsNone(
            beast_rally_expanded_capacity_baseline(
                (True,) * 6, None, cap(0, 6)
            )
        )

    def test_full_capacity_never_authorises_a_new_rally(self):
        self.assertIsNone(
            beast_rally_expanded_capacity_baseline(
                (False,) * 6, cap(6, 6), cap(6, 6)
            )
        )

    def fixed_search_context(self, *, town: bool = True, collapsed: bool = True) -> Image.Image:
        frame = Image.new("RGB", (1440, 2560), (18, 53, 88))
        if town:
            paste_centre(frame, BUILTIN_BEAST_RALLY_WORLD_TOWN_DENSE_ASSET, (1319, 2370))
        if collapsed:
            paste_centre(
                frame,
                BUILTIN_BEAST_RALLY_PROGRESS_SIDEBAR_COLLAPSED_ASSET,
                (45, 1111),
            )
        return frame

    def test_dual_context_exposes_fixed_search_without_search_skin(self):
        point, _score = match_beast_rally_world_search(
            self.fixed_search_context(), 0.90
        )
        self.assertEqual(point, (90, 1754))

    def test_fixed_search_requires_town(self):
        point, _score = match_beast_rally_world_search(
            self.fixed_search_context(town=False), 0.90
        )
        self.assertIsNone(point)

    def test_fixed_search_requires_collapsed_panel(self):
        point, _score = match_beast_rally_world_search(
            self.fixed_search_context(collapsed=False), 0.90
        )
        self.assertIsNone(point)

    def test_capacity_monitor_opens_panel_before_reading_expanded_header(self):
        source = (ROOT / "wjdr_mumu_assistant_qt.py").read_text(encoding="utf-8")
        monitor = source.split("def monitor_dispatched_queue", 1)[1].split(
            "def configure_level", 1
        )[0]
        open_index = monitor.index('open_wilderness_queue_panel(\n                        "出征后复核野外容量"')
        read_index = monitor.index("read_beast_rally_expanded_march_capacity")
        self.assertLess(open_index, read_index)


if __name__ == "__main__":
    unittest.main()
