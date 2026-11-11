"""Single-shield setup uses a proven plus once, never a numeric input."""
import ast
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image, ImageDraw, ImageEnhance
import wjdr_mumu_assistant_qt as qt


class SingleShieldPlusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        config_patch = patch.object(qt, 'CONFIG_DIR', Path(self.tmp.name))
        config_patch.start()
        self.addCleanup(config_patch.stop)
        self.image = Image.new('RGB', (1440, 2560), (40, 40, 40))
        with Image.open('assets/beast_soldier_types.png') as icons:
            self.image.paste(icons.crop((0, 0, 56, 50)), (52, 1298))
        with Image.open('tests/fixtures/beast_first_shield_plus.png') as plus:
            self.image.paste(plus, (1260, 1380))

    def test_real_plus_requires_cleared_shield_and_visible_control(self):
        cleared = lambda _: (0, 0, (135, 2365))
        self.assertEqual(qt.beast_cleared_first_shield_plus(self.image, cleared), (1317, 1434))
        self.assertEqual(qt.beast_cleared_first_shield_plus(self.image.resize((720, 1280)), cleared), (658, 717))
        dimmed = ImageEnhance.Brightness(self.image).enhance(.5)
        self.assertIsNone(qt.beast_cleared_first_shield_plus(dimmed, cleared))
        damaged = self.image.copy()
        ImageDraw.Draw(damaged).rectangle((1300, 1410, 1330, 1455), fill='blue')
        self.assertIsNone(qt.beast_cleared_first_shield_plus(damaged, cleared))
        for state in (None, (1, 1, (135, 2365)), (5, 0, (135, 2365))):
            self.assertIsNone(qt.beast_cleared_first_shield_plus(self.image, lambda _: state))

    def test_second_row_shield_uses_second_plus_and_rejects_ambiguous_first_row(self):
        with Image.open('tests/fixtures/beast_shield_second_row_icons.png') as icons:
            self.image.paste(icons.crop((0, 0, 72, 66)), (44, 1290))
            self.image.paste(icons.crop((0, 66, 72, 132)), (44, 1570))
        with Image.open('tests/fixtures/beast_first_shield_plus.png') as plus:
            self.image.paste(plus, (1260, 1660))
        cleared = lambda _: (0, 0, (135, 2365))
        self.assertEqual(qt.beast_cleared_first_shield_plus(self.image, cleared), (1317, 1714))
        ImageDraw.Draw(self.image).rectangle((44, 1290, 116, 1356), fill='black')
        self.assertIsNone(qt.beast_cleared_first_shield_plus(self.image, cleared))

    def run_setup(self, state, clear_ok=True, result_ok=True):
        tree = ast.parse(Path('wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8'))
        function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                        and n.name == 'configure_single_shield')
        target = SimpleNamespace(device='device', tap=Mock(), shell=Mock(), check_active=Mock())
        waits = []
        def wait(label, matcher):
            waits.append(label)
            if '加号' in label:
                return (self.image, (1317, 1434), None) if clear_ok else None
            return (self.image, (1, 1), None) if result_ok else None
        env = dict(Image=Image, Any=object, wanted_troops=(1, 0, 0), completed_cycles=0,
                   capture=Mock(return_value=self.image), beast_mixed_single_shield=Mock(return_value=state),
                   wait_for_double=wait, target=target, exact_formation_match=Mock(),
                   self=SimpleNamespace(_log_for_device=Mock()), beast_cleared_first_shield_plus=Mock(),
                   identity='index-9-android-id', beast_shield_plus_pending=qt.beast_shield_plus_pending,
                   beast_shield_plus_claim=qt.beast_shield_plus_claim,
                   beast_shield_plus_confirm=qt.beast_shield_plus_confirm, threshold=.8,
                   match_beast_rally_formation_controls=Mock(return_value=SimpleNamespace(point=(1087, 2391))),
                   action_positions=SimpleNamespace(remember=Mock(side_effect=lambda name, image, point: point),
                                                    cached_point=Mock(return_value=(1087, 2391))))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), 'setup', 'exec'), env)
        return env['configure_single_shield'](), target, waits

    def test_clears_and_returns_first_recognized_positions(self):
        result, target, waits = self.run_setup((100, 50, (135, 2365)))
        self.assertEqual(result, ((1317, 1434), (1087, 2391), 25))
        self.assertEqual(target.tap.call_args_list, [unittest.mock.call(135, 2365)])
        target.shell.assert_not_called()
        self.assertEqual(len(waits), 1)

    def test_unverified_clear_or_plus_never_adds(self):
        result, target, _ = self.run_setup((100, 50, (135, 2365)), clear_ok=False)
        self.assertFalse(result)
        target.tap.assert_called_once_with(135, 2365)

    def test_pending_plus_does_not_repeat_setup(self):
        self.assertTrue(qt.beast_shield_plus_claim('index-9-android-id'))
        result, restarted_target, _ = self.run_setup((0, 0, (135, 2365)))
        self.assertFalse(result)
        restarted_target.tap.assert_not_called()

    def test_marker_is_exclusive_and_account_scoped(self):
        self.assertTrue(qt.beast_shield_plus_claim('device-a'))
        self.assertFalse(qt.beast_shield_plus_claim('device-a'))
        self.assertTrue(qt.beast_shield_plus_claim('device-b'))
        qt.beast_shield_plus_confirm('device-a')
        self.assertFalse(qt.beast_shield_plus_pending('device-a'))
        self.assertTrue(qt.beast_shield_plus_pending('device-b'))

    def test_receipt_rejects_ambiguous_or_obscured_frames(self):
        first, second = object(), object()
        state = Mock(return_value=(1, 1, (135, 2365)))
        controls = Mock(return_value=(1087, 2391))
        network = Mock(return_value=False)
        receipt = lambda: qt.beast_shield_plus_receipt(first, second, state, controls, network)
        self.assertTrue(receipt())
        state.side_effect = [(1, 1, (135, 2365)), (0, 0, (135, 2365))]
        self.assertFalse(receipt())
        state.side_effect = None
        controls.side_effect = [(1087, 2391), None]
        self.assertFalse(receipt())
        controls.side_effect = None
        network.return_value = True
        self.assertFalse(receipt())

    def test_existing_single_is_cleared_before_cached_setup(self):
        result, target, _ = self.run_setup((1, 1, (135, 2365)))
        self.assertTrue(result)
        target.tap.assert_called_once_with(135, 2365)

    def test_fast_dispatch_claims_and_reserves_before_plus_then_waits_50ms(self):
        events = []
        target = SimpleNamespace(check_active=lambda: events.append('active'),
                                 tap=lambda *point: events.append(('tap', point)))
        stop = SimpleNamespace(wait=lambda seconds: events.append(('wait', seconds)) or False)
        with patch.object(qt, 'beast_shield_plus_claim', side_effect=lambda identity: events.append('claim') or True), \
             patch.object(qt, 'reserve_beast_rally_stamina', side_effect=lambda identity, cost: events.append(('reserve', cost))):
            self.assertTrue(qt.beast_fast_single_shield_dispatch('account', 25, (1, 2), (3, 4), target, stop))
        self.assertEqual(events, ['active', 'claim', ('reserve', 25), 'active',
                                  ('tap', (1, 2)), ('wait', .05), ('tap', (3, 4))])

    def test_fast_dispatch_stop_keeps_marker_and_never_repeats(self):
        target = SimpleNamespace(check_active=Mock(), tap=Mock())
        stop = SimpleNamespace(wait=Mock(return_value=True))
        with patch.object(qt, 'reserve_beast_rally_stamina') as reserve:
            self.assertFalse(qt.beast_fast_single_shield_dispatch('account', 25, (1, 2), (3, 4), target, stop))
            self.assertTrue(qt.beast_shield_plus_pending('account'))
            self.assertFalse(qt.beast_fast_single_shield_dispatch('account', 25, (1, 2), (3, 4), target, stop))
        reserve.assert_called_once_with('account', 25)
        target.tap.assert_called_once_with(1, 2)

    def test_fast_dispatch_reservation_failure_never_taps(self):
        target = SimpleNamespace(check_active=Mock(), tap=Mock())
        with patch.object(qt, 'reserve_beast_rally_stamina', side_effect=RuntimeError('reserve failed')):
            with self.assertRaises(RuntimeError):
                qt.beast_fast_single_shield_dispatch('account', 25, (1, 2), (3, 4), target, Mock())
        target.tap.assert_not_called()
        self.assertTrue(qt.beast_shield_plus_pending('account'))

    def test_cached_dispatch_reserves_estimate_before_clear_and_never_repeats(self):
        target = SimpleNamespace(check_active=Mock(), tap=Mock())
        stop = SimpleNamespace(wait=Mock(return_value=False), is_set=Mock(return_value=False))
        with patch.object(qt, 'reserve_beast_rally_stamina') as reserve:
            self.assertTrue(qt.beast_fast_single_shield_dispatch(
                'account', 25, (1, 2), (3, 4), target, stop, clear=(5, 6), estimated=True))
            reserve.assert_called_once_with('account', 25, estimated=True)
            self.assertEqual(target.tap.call_args_list, [unittest.mock.call(5, 6),
                             unittest.mock.call(1, 2), unittest.mock.call(3, 4)])
            self.assertFalse(qt.beast_fast_single_shield_dispatch(
                'account', 25, (1, 2), (3, 4), target, stop, clear=(5, 6), estimated=True))
            self.assertEqual(target.tap.call_count, 3)


if __name__ == '__main__':
    unittest.main()
