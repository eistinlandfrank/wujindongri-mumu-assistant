import threading
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image, ImageEnhance
import wjdr_scoreboard as scores
from wjdr_backend import resource_path
from wjdr_scoreboard_ui import ScoreboardUI


class NavigationSafetyTest(unittest.TestCase):
    def test_ranking_access_with_either_selected_kingdom_tab(self):
        def line(text, x, y):
            return {'text': text, 'words': [{'text': text, 'x': x, 'y': y}]}
        lines = [line('常规活动', 194, 46), line('最强王国', 89, 438),
                 line('排行榜', 944, 818), line('备战阶段', 313, 1107),
                 line('子阶段目标', 918, 1111)]
        frame = Image.new('RGB', (1440, 2560))
        with patch.object(scores, 'match_daily_regular_activity_back', return_value=(True, 1.0)):
            frame.paste((240, 190, 130), (740, 1060, 1350, 1190))
            self.assertEqual(scores.navigation_decision(frame, lines), ('open_ranking', (1245, 930)))
            self.assertIsNone(scores.navigation_decision(frame, lines[:-1]))
            frame.paste((0, 0, 0), (740, 1060, 1350, 1190))
            self.assertIsNone(scores.navigation_decision(frame, lines))
            frame.paste((240, 190, 130), (100, 1060, 650, 1190))
            self.assertEqual(scores.navigation_decision(frame, lines), ('open_ranking', (1245, 930)))

    def test_only_known_shop_title_and_close_glyph_allow_dismissal(self):
        frame = Image.new('RGB', (1440, 2560))
        close = Image.open(resource_path('assets/scoreboard_shop_close.png')).convert('RGB')
        frame.paste(close, (1275, 395))
        title = [{'text': '铸匠的珍藏', 'words': [{'text': '铸匠的珍藏', 'x': 75, 'y': 388}]}]
        self.assertEqual(scores.navigation_decision(frame, title), ('close_known_shop', (1332, 457)))
        with patch.object(scores, 'match_world_control_interiors', return_value=(False, False, 0)):
            self.assertIsNone(scores.navigation_decision(frame, []))
            self.assertIsNone(scores.navigation_decision(ImageEnhance.Brightness(frame).enhance(.5), title))

    def test_world_requires_both_controls_and_undimmed_icon(self):
        frame = Image.new('RGB', (1440, 2560))
        icon = Image.open(resource_path('assets/scoreboard_activity_icon.png')).convert('RGB')
        frame.paste(icon, (1290, 255))
        with patch.object(scores, 'match_world_control_interiors', return_value=(True, True, 1.0)):
            self.assertEqual(scores.navigation_decision(frame, []), ('open_activities', (1325, 295)))
            self.assertIsNone(scores.navigation_decision(ImageEnhance.Brightness(frame).enhance(.5), []))
            self.assertIsNone(scores.navigation_decision(Image.new('RGB', frame.size), []))
        with patch.object(scores, 'match_world_control_interiors', return_value=(True, False, 1.0)):
            self.assertIsNone(scores.navigation_decision(frame, []))

    def run_navigation(self, decision):
        ui = ScoreboardUI()
        ui.stop_event = threading.Event()
        ui.log = lambda message: None
        ui._score_run_ocr = MagicMock(return_value=[])
        target = MagicMock()
        target.device = 'selected'
        target.foreground_is_game.return_value = True
        target.screenshot.return_value = Image.new('RGB', (1440, 2560))
        with patch('wjdr_scoreboard_identity.verify_bound_identity', return_value=True), \
             patch.object(scores, 'navigation_decision', return_value=decision), \
             patch.object(Image.Image, 'save'):
            with self.assertRaises(ValueError):
                ui._score_navigation(target, 'mumu:2:android:abc123')
        return target

    def test_unknown_page_never_sends_input(self):
        self.assertEqual(self.run_navigation(None).shell.call_count, 0)

    def test_unacknowledged_action_is_not_repeated(self):
        target = self.run_navigation(('open_ranking', (1245, 930)))
        self.assertEqual(target.shell.call_count, 1)
        self.assertEqual(target.screenshot.call_count, 6)

    def test_transient_obscured_frame_is_reobserved_before_input(self):
        ui = ScoreboardUI()
        ui.stop_event = threading.Event()
        ui.score_editor_identity = None
        ui.score_table = MagicMock()
        ui.score_table.rowCount.return_value = 0
        ui.log = MagicMock()
        ui.signals = MagicMock()
        ui._score_identity = lambda: 'mumu:2:android:abc123'
        ui._score_navigation = MagicMock()
        ui._score_error = MagicMock(side_effect=AssertionError)
        target = MagicMock()
        target.device = 'selected'
        target.foreground_is_game.return_value = True
        target.screenshot.return_value = Image.new('RGB', (1440, 2560))
        ui.adb = MagicMock()
        ui.adb.clone_for_device.return_value = target
        rows = [dict(rank='1', country='#523', alliance='RMB', name='name', score=100)]
        ui._score_read_frame = MagicMock(side_effect=[ValueError('temporary overlay'),
                                                       {'identity': ui._score_identity(), 'rows': rows, 'text': ''}])
        ui._start_worker = lambda device, job, expected_identity: job()
        with patch.object(scores, 'save_capture_draft', side_effect=lambda *args: ui.stop_event.set()):
            ui._score_capture_many()
        self.assertEqual(ui._score_read_frame.call_count, 2)
        self.assertEqual(target.shell.call_count, 0)
        self.assertEqual(ui.signals.score_ocr.emit.call_count, 1)

    def test_pre_swipe_confirmation_retries_obstruction_without_input(self):
        ui = ScoreboardUI()
        ui.stop_event = threading.Event()
        target = MagicMock()
        target.device = 'selected'
        target.foreground_is_game.return_value = True
        frame = Image.new('RGB', (1440, 2560))
        target.screenshot.return_value = frame
        with patch('wjdr_scoreboard_identity.verify_bound_identity', return_value=True), \
             patch.object(scores, 'validate_total_selection', side_effect=[ValueError('obscured'), None]):
            self.assertTrue(ui._score_confirm_swipe(target, 'mumu:2:android:abc123', frame))
        self.assertEqual(target.screenshot.call_count, 2)
        self.assertEqual(target.shell.call_count, 0)


if __name__ == '__main__':
    unittest.main()
