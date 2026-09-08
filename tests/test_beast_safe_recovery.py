"""Focused recovery faults: no real game inputs, sleeps, or account writes."""
import ast
import threading
import unittest
from typing import Callable, Any
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PIL import Image, ImageDraw

from wjdr_backend import AdbError, DailyMarchCapacity, BeastRallyState
from wjdr_beast_hunt import GuardedBeastADB, SingleBeastCycle, CompactRallyRow, read_compact_capacity
from wjdr_beast_hunt import only_joined_rallies


class ReadRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.raw = Mock(device='new-adb')
        self.stop = threading.Event()
        self.report = Mock()
        self.guard = GuardedBeastADB(self.raw, self.stop, self.report)

    def test_transient_capture_recovers_fresh_without_input(self):
        frame = object()
        self.raw.screenshot.side_effect = [AdbError('truncated PNG'), frame]
        self.assertIs(self.guard.screenshot(), frame)
        self.assertEqual(self.raw.screenshot.call_count, 2)
        self.raw.tap.assert_not_called()
        self.raw.connect.assert_not_called()
        self.report.assert_called_once()

    def test_repeated_capture_failure_has_three_attempt_cap(self):
        self.raw.screenshot.side_effect = AdbError('offline')
        with self.assertRaises(AdbError):
            self.guard.screenshot()
        self.assertEqual(self.raw.screenshot.call_count, 3)
        self.assertTrue(all(0 < c.kwargs['timeout'] <= 2.5 for c in self.raw.screenshot.call_args_list))

    def test_stopped_guard_blocks_all_input_paths(self):
        self.stop.set()
        for action in [lambda: self.guard.tap(1, 2), self.guard.back,
                       lambda: self.guard.shell(['input', 'text', '8']), self.guard.screenshot]:
            with self.assertRaises(InterruptedError):
                action()
        self.assertEqual(self.raw.mock_calls, [])

    def test_stopping_during_capture_discards_frame(self):
        self.raw.screenshot.side_effect = lambda **_: self.stop.set()
        with self.assertRaises(InterruptedError):
            self.guard.screenshot()
        self.raw.tap.assert_not_called()

    def test_failed_input_is_never_replayed(self):
        self.raw.tap.side_effect = AdbError('unknown acknowledgement')
        with self.assertRaises(AdbError):
            self.guard.tap(1, 2)
        self.raw.tap.assert_called_once_with(1, 2)

    def test_rebound_adb_does_not_migrate_recovery(self):
        self.raw.device = 'another-account'
        with self.assertRaises(AdbError):
            self.guard.screenshot()
        self.raw.screenshot.assert_not_called()


def nested(name, env):
    source = ast.parse(Path('wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8'))
    fn = next(n for n in ast.walk(source) if isinstance(n, ast.FunctionDef) and n.name == name)
    # Preserve the real nonlocal state as this isolated fixture's global.
    class Bind(ast.NodeTransformer):
        def visit_Nonlocal(self, node):
            return ast.copy_location(ast.Global(names=node.names), node)
    env.setdefault('blue_pair_free', lambda *_: False)
    fn = Bind().visit(fn)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), name, 'exec'), env)
    return env[name]


class CompactRecoveryTest(unittest.TestCase):
    def test_missing_hunt_prompts_after_two_formation_frames(self):
        alert, capture = Mock(), Mock(return_value=object())
        env = dict(Callable=Callable, Any=Any, Image=Image, AUTOMATION_STEP_TIMEOUT_SECONDS=24,
                   bounded_step_timeout=lambda x: x, time=SimpleNamespace(monotonic=Mock(side_effect=range(20))),
                   self=SimpleNamespace(stop_event=threading.Event(), _log_for_device=Mock(),
                                        signals=SimpleNamespace(alert=SimpleNamespace(emit=alert))),
                   capture=capture, daily_network_dialog_is_visible=lambda *_: False,
                   threshold=.9, match_beast_rally_formation_controls=lambda *_: SimpleNamespace(state=BeastRallyState.FORMATION),
                   BeastRallyState=BeastRallyState, set_state=Mock(), pause=lambda: False,
                   APP_NAME='test', target=SimpleNamespace(device='new-adb'))
        result = nested('wait_for_double', env)('确认出征编组页面', lambda _: (None, None))
        self.assertIsNone(result)
        self.assertEqual(capture.call_count, 2)
        alert.assert_called_once()

    def baseline(self, frames):
        frame_iter = iter(frames)
        env = dict(ensure_compact_march_panel=Mock(return_value=True),
                   time=SimpleNamespace(monotonic=Mock(side_effect=range(0, 500, 3))),
                   self=SimpleNamespace(stop_event=threading.Event(), _log_for_device=Mock()),
                   target=SimpleNamespace(device='new-adb'), capture=lambda: next(frame_iter),
                   read_compact_rally_rows=lambda _: (), only_joined_rallies=only_joined_rallies,
                   read_beast_rally_collapsed_march_capacity=lambda image, _: image,
                   threshold=.9, set_state=Mock(), pause=lambda: False,
                   open_wilderness_queue_panel=Mock(), baseline_march_capacity=None)
        return nested('single_team_baseline', env)(), env

    def test_missing_then_valid_compact_pair_resumes(self):
        idle = DailyMarchCapacity(0, 6, 1.0)
        result, env = self.baseline([None, None, idle, idle])
        self.assertTrue(result)
        self.assertEqual(env['baseline_march_capacity'], (0, 6))
        env['open_wilderness_queue_panel'].assert_not_called()

    def test_missing_header_times_out_not_zero(self):
        result, env = self.baseline([None] * 30)
        self.assertFalse(result)
        self.assertIsNone(env['baseline_march_capacity'])
        env['open_wilderness_queue_panel'].assert_not_called()

    def test_mismatched_capacity_pair_does_not_authorize(self):
        idle, busy = DailyMarchCapacity(0, 6, 1.), DailyMarchCapacity(1, 6, 1.)
        result, _ = self.baseline([idle, busy] * 15)
        self.assertFalse(result)

    def test_expanded_overlay_is_collapsed_never_opened(self):
        close = Mock(return_value=True)
        env = dict(capture=Mock(return_value=object()), threshold=.9,
                   match_beast_rally_progress_sidebar_expanded=Mock(return_value=((10, 20), .99)),
                   stable=lambda p, q: bool(p and q and p == q),
                   self=SimpleNamespace(_log_for_device=Mock()), target=SimpleNamespace(device='new-adb'),
                   collapse_wilderness_queue_panel=close, open_wilderness_queue_panel=Mock())
        self.assertTrue(nested('ensure_compact_march_panel', env)())
        close.assert_called_once()
        env['open_wilderness_queue_panel'].assert_not_called()

    def test_monitor_keeps_owned_cycle_through_unknown_to_return(self):
        busy, idle = DailyMarchCapacity(1, 5, 1.), DailyMarchCapacity(0, 0, .95, 'hidden_idle')
        frames = iter(['own', 'own'] + [None] * 60 + [busy, busy, idle, idle])
        confirm, repair = Mock(return_value=20), Mock(return_value=True)
        env = dict(baseline_march_capacity=(0, 0), SingleBeastCycle=SingleBeastCycle,
                   match_same_target_conflict=lambda _:None,
                   only_joined_rallies=only_joined_rallies, read_compact_marching_rows=lambda _: (),
                   time=SimpleNamespace(monotonic=Mock(side_effect=range(200))),
                   match_world=lambda _: ((90,1754), 1),
                   ensure_compact_march_panel=repair, capture=lambda: next(frames),
                   read_compact_rally_rows=lambda im: (CompactRallyRow('own', (80, 500), 60),) if im == 'own' else (),
                   read_beast_rally_collapsed_march_capacity=lambda im, _: im,
                   stable=lambda p, q: p == q, threshold=.9, identity='test',
                   confirm_beast_rally_stamina_reservation=confirm,
                   self=SimpleNamespace(stop_event=threading.Event(), _log_for_device=Mock()),
                   target=SimpleNamespace(device='new-adb'), set_state=Mock(), save_evidence=Mock(),
                   pause=lambda: False, recover_pending_reservation=Mock(),
                   open_wilderness_queue_panel=Mock())
        self.assertTrue(nested('monitor_single_team', env)())
        confirm.assert_called_once_with('test')
        self.assertEqual(repair.call_count, 1)  # only upon unreadable state
        env['open_wilderness_queue_panel'].assert_not_called()
        env['recover_pending_reservation'].assert_not_called()

    def test_owned_march_finishes_with_only_joined_rally_remaining(self):
        frames=iter(['own','own','march','march','joined','joined'])
        env=dict(baseline_march_capacity=(0,6),SingleBeastCycle=SingleBeastCycle,
                 match_same_target_conflict=lambda _:None,
                 time=SimpleNamespace(monotonic=Mock(side_effect=range(200))),
                 capture=lambda: next(frames),threshold=.9,identity='test',
                 read_compact_rally_rows=lambda im: (CompactRallyRow('own' if im=='own' else 'joined',(70,530),60),) if im in ('own','joined') else (),
                 read_compact_marching_rows=lambda im: (CompactRallyRow('own',(72,540),16,'marching'),) if im=='march' else (),
                 read_beast_rally_collapsed_march_capacity=lambda im,_: DailyMarchCapacity(1,6,1),
                 only_joined_rallies=only_joined_rallies,stable=lambda p,q:p==q,
                 confirm_beast_rally_stamina_reservation=Mock(return_value=20),
                 self=SimpleNamespace(stop_event=threading.Event(),_log_for_device=Mock()),
                 target=SimpleNamespace(device='test'),set_state=Mock(),save_evidence=Mock(),
                 pause=lambda:False)
        self.assertTrue(nested('monitor_single_team',env)())
        self.assertEqual(env['save_evidence'].call_args.args[2],'hunt_done_allied_remaining')

    def test_target_conflict_cancel_restore_and_retry_without_completion(self):
        import wjdr_backend as b
        target=Mock(device='test')
        release=Mock()
        env=dict(match_same_target_conflict=lambda _: (420,1580),stable=lambda p,q:bool(p and q and p==q),
                 target_conflicts=0,retry_target_requested=False,target=target,
                 self=SimpleNamespace(_log_for_device=Mock(),stop_event=threading.Event()),save_evidence=Mock(),
                 wait_for_double=Mock(return_value=('formation',(1,2),None)),
                 exact_formation_match=Mock(),capture=Mock(side_effect=['formation','world','world']),
                 read_beast_rally_dispatch_stamina=Mock(return_value=20),
                 match_hunt_formation=Mock(return_value=SimpleNamespace(state=b.BeastRallyState.FORMATION)),
                 BeastRallyState=b.BeastRallyState,identity='account-a',
                 load_beast_rally_stamina_reserved=Mock(return_value=20),
                 cancel_beast_rally_conflict_reservation=release,
                 match_beast_rally_open_button=Mock(return_value=(None,0)),threshold=.9,
                 ensure_wilderness=Mock(return_value=True))
        self.assertTrue(nested('resolve_target_conflict',env)('warning','warning'))
        target.tap.assert_called_once_with(420,1580)
        target.back.assert_called_once()
        release.assert_called_once_with('account-a',20,cancelled_and_formation_restored=True)
        self.assertTrue(env['retry_target_requested'])
        self.assertEqual(env['target_conflicts'],1)
        env['target_conflicts']=3
        target.reset_mock()
        self.assertFalse(nested('resolve_target_conflict',env)('warning','warning'))
        target.tap.assert_not_called()

    def test_compact_reservation_recovery_keeps_uncertain_budget(self):
        import tempfile
        from wjdr_backend import (reserve_beast_rally_stamina, reconcile_beast_rally_idle_reservation,
                                 load_beast_rally_stamina_uncertain)
        with tempfile.TemporaryDirectory() as folder:
            opts = dict(path=Path(folder)/'ledger.json', day='2026-09-06')
            reserve_beast_rally_stamina('test', 20, **opts)
            idle = DailyMarchCapacity(0, 6, 1.)
            for expected in (20, 0):
                self.assertEqual(reconcile_beast_rally_idle_reservation('test', None, None,
                                 first_capacity=idle, second_capacity=idle, **opts), expected)
            self.assertEqual(load_beast_rally_stamina_uncertain('test', **opts), 20)


class HiddenIdleTest(unittest.TestCase):
    def read(self, image):
        with patch('wjdr_beast_hunt.read_beast_rally_collapsed_march_capacity', return_value=None), \
             patch('wjdr_beast_hunt.match_beast_rally_world_search', return_value=((90,1754),1)), \
             patch('wjdr_beast_hunt.match_beast_rally_progress_sidebar_collapsed', return_value=((45,1111),1)), \
             patch('wjdr_beast_hunt.match_beast_rally_progress_sidebar_expanded', return_value=(None,0)), \
             patch('wjdr_beast_hunt.read_compact_rally_rows', return_value=()):
            return read_compact_capacity(image)

    def test_hidden_list_idle_scales_without_fabricating_six_slots(self):
        for size in [(720,1280), (1080,1920), (1440,2560)]:
            value = self.read(Image.new('RGB', size, (130,160,200)))
            self.assertEqual((value.used, value.total, value.evidence), (0,0,'hidden_idle'))

    def test_visible_header_without_digits_is_not_idle(self):
        frame = Image.new('RGB', (1440,2560), (130,160,200))
        with Image.open('assets/beast_rally_compact_march_title.png') as title:
            frame.paste(title.resize((100,52)), (90,400))
        for size in [(1080,1920), (1440,2560)]:
            self.assertIsNone(self.read(frame.resize(size)))

    def test_countdown_bar_without_title_is_not_idle(self):
        frame = Image.new('RGB', (1440,2560), (130,160,200))
        ImageDraw.Draw(frame).rectangle((110,500,390,535), fill=(15,15,15))
        self.assertIsNone(self.read(frame))

    def test_wrong_aspect_or_too_small_is_rejected(self):
        for size in [(1440,1920), (2560,1440), (360,640)]:
            self.assertIsNone(self.read(Image.new('RGB', size, (130,160,200))))


if __name__ == '__main__':
    unittest.main()
