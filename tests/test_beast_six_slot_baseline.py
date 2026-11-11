"""Six-team policy uses fresh physical slots, not stale virtual row counts."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from wjdr_beast_hunt import ConcurrentRallySnapshot, concurrent_dispatch_allowed, confirms_new_concurrent_rally


class SixSlotBaselineTest(unittest.TestCase):
    def baseline(self, snapshot, limit, sequence=None, pause=None, conflict=None):
        tree = ast.parse(Path('wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8'))
        function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                        and n.name == 'concurrent_baseline')
        class Globals(ast.NodeTransformer):
            def visit_Nonlocal(self, node):
                return ast.copy_location(ast.Global(names=node.names), node)
        function = Globals().visit(function)
        tracker = SimpleNamespace(observe=Mock(return_value=True), has_room=Mock(return_value=False))
        frames = iter(sequence) if sequence is not None else None
        env = dict(
            baseline_concurrent=None, baseline_march_capacity=None,
            tracked_green=0, tracked_rallies=0, line_tracker=tracker,
            ensure_compact_march_panel=lambda: True,
            capture=lambda: next(frames) if frames is not None else object(),
            read_concurrent_snapshot=lambda image: getattr(image, 'snapshot', image) if frames is not None else snapshot,
            read_beast_rally_collapsed_march_capacity=lambda image: getattr(image, 'capacity', None),
            read_compact_numeric_capacity=lambda image: getattr(image, 'capacity', None),
            match_world=lambda image: (getattr(image, 'world', True), 1),
            ConcurrentRallySnapshot=ConcurrentRallySnapshot,
            match_same_target_conflict=conflict or (lambda _: None),
            stable=lambda a, b: bool(a and b),
            daily_network_dialog_is_visible=lambda frame, threshold: False, threshold=0.9,
            profile=SimpleNamespace(max_concurrent_rallies=limit),
            self=SimpleNamespace(stop_event=SimpleNamespace(is_set=lambda: False),
                                 _log_for_device=Mock()),
            target=SimpleNamespace(device='test'),
            time=SimpleNamespace(monotonic=Mock(side_effect=range(0, 400, 5))),
            set_state=Mock(), pause=pause or (lambda: True),
            concurrent_dispatch_allowed=concurrent_dispatch_allowed,
        )
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                     'baseline', 'exec'), env)
        return env['concurrent_baseline'](), env, tracker

    def test_four_of_six_with_green_and_stale_tracker_dispatches(self):
        snap = ConcurrentRallySnapshot(4, 6, 'numeric', ('rallying', 'rallying', 'marching', 'marching'))
        allowed, env, tracker = self.baseline(snap, 6)
        self.assertTrue(allowed)
        self.assertEqual(env['baseline_march_capacity'], (4, 6))
        tracker.has_room.assert_not_called()

    def test_full_six_does_not_dispatch(self):
        snap = ConcurrentRallySnapshot(6, 6, 'numeric', ('marching',) * 6)
        allowed, _, _ = self.baseline(snap, 6)
        self.assertFalse(allowed)

    def test_stable_numeric_four_of_six_with_unknown_rows_dispatches_conservatively(self):
        frame = SimpleNamespace(snapshot=None, capacity=SimpleNamespace(used=4, total=6, evidence='numeric'))
        allowed, env, _ = self.baseline(None, 6, [frame, frame])
        self.assertTrue(allowed)
        self.assertEqual(env['baseline_concurrent'], ConcurrentRallySnapshot(4, 6, 'numeric', ('unknown',) * 4))
        self.assertEqual(env['baseline_march_capacity'], (4, 6))

    def test_unknown_baseline_never_confirms_capacity_increase_alone(self):
        before = ConcurrentRallySnapshot(4, 6, 'numeric', ('unknown',) * 4)
        ambiguous = ConcurrentRallySnapshot(5, 6, 'numeric', ('rallying',) * 4 + ('blue',))
        proven = ConcurrentRallySnapshot(5, 6, 'numeric', ('rallying',) * 5)
        self.assertFalse(confirms_new_concurrent_rally(before, ambiguous))
        self.assertTrue(confirms_new_concurrent_rally(before, proven))
        self.assertFalse(confirms_new_concurrent_rally(before, ConcurrentRallySnapshot(5, 6, 'numeric', ('unknown',) * 5)))

    def test_unknown_rows_can_recover_when_two_known_frames_arrive(self):
        unreadable = SimpleNamespace(snapshot=None, capacity=None)
        snap = ConcurrentRallySnapshot(4, 6, 'numeric', ('blue', 'blue', 'marching', 'rallying'))
        known = SimpleNamespace(snapshot=snap)
        allowed, env, _ = self.baseline(None, 6, [unreadable, unreadable, known, known], lambda: False)
        self.assertTrue(allowed)
        self.assertEqual(env['baseline_concurrent'], snap)
        after = ConcurrentRallySnapshot(5, 6, 'numeric', ('blue', 'blue', 'marching', 'rallying', 'rallying'))
        self.assertTrue(confirms_new_concurrent_rally(snap, after))

    def test_numeric_zero_without_readable_rows_waits(self):
        frame = SimpleNamespace(snapshot=None, capacity=SimpleNamespace(used=0, total=6, evidence='numeric'))
        allowed, env, _ = self.baseline(None, 6, [frame, frame])
        self.assertFalse(allowed)
        self.assertIsNone(env['baseline_concurrent'])

    def test_partial_numeric_fails_when_capacity_changes_or_is_full_or_world_unknown(self):
        def frame(used, total=6, world=True):
            return SimpleNamespace(snapshot=None, capacity=SimpleNamespace(used=used, total=total, evidence='numeric'), world=world)
        for first, second in ((frame(4), frame(5)), (frame(6), frame(6)),
                              (frame(4, world=False), frame(4))):
            with self.subTest(first=first, second=second):
                allowed, _, _ = self.baseline(None, 6, [first, second])
                self.assertFalse(allowed)

    def test_other_limits_retain_owned_line_tracking(self):
        snap = ConcurrentRallySnapshot(1, 6, 'numeric', ('blue',))
        allowed, _, tracker = self.baseline(snap, 2)
        self.assertFalse(allowed)
        tracker.has_room.assert_called_once_with(2)

    def test_unknown_frames_after_timeout_wait_until_known(self):
        snap = ConcurrentRallySnapshot(4, 6, 'numeric', ('rallying', 'rallying', 'marching', 'marching'))
        allowed, env, _ = self.baseline(snap, 6, [None] * 12 + [snap, snap], lambda: False)
        self.assertTrue(allowed)
        self.assertGreater(env['set_state'].call_count, 0)

    def test_stable_conflict_stops(self):
        snap = ConcurrentRallySnapshot(0, 6, 'numeric', ())
        allowed, _, _ = self.baseline(snap, 6, conflict=lambda _: (1, 1))
        self.assertFalse(allowed)


if __name__ == '__main__':
    unittest.main()
