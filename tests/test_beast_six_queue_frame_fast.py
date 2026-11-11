"""Six-team queue decisions use one fresh frame and actual capacity."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from wjdr_beast_hunt import ConcurrentRallySnapshot


class SixQueueFrameFastTest(unittest.TestCase):
    def run_queue(self, seed, later=(), pause=None, limit=6):
        tree = ast.parse(Path('wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8'))
        function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                        and n.name == 'wait_queue_capacity_frame')

        class Globals(ast.NodeTransformer):
            def visit_Nonlocal(self, node):
                return ast.copy_location(ast.Global(names=node.names), node)

        frames = iter(later)
        capture = Mock(side_effect=lambda: next(frames))
        ensure = Mock(return_value=True)
        env = {
            'baseline_concurrent': None, 'baseline_march_capacity': None,
            'self': SimpleNamespace(stop_event=SimpleNamespace(is_set=lambda: False),
                                    _log_for_device=Mock()),
            'target': SimpleNamespace(device='test'), 'threshold': .9,
            'profile': SimpleNamespace(max_concurrent_rallies=limit),
            'capture': capture, 'ensure_compact_march_panel': ensure,
            'daily_network_dialog_is_visible': lambda image, threshold: getattr(image, 'network', False),
            'match_beast_rally_progress_sidebar_expanded': lambda image, threshold: (getattr(image, 'expanded', False), 1),
            'match_world': lambda image: (getattr(image, 'search', None), 1),
            'read_beast_rally_collapsed_march_capacity': lambda image, threshold, *, world_proven=False: getattr(image, 'capacity', None) if world_proven else None,
            'ConcurrentRallySnapshot': ConcurrentRallySnapshot,
            'set_state': Mock(), 'pause': pause or (lambda: False),
        }
        exec(compile(ast.fix_missing_locations(ast.Module(body=[Globals().visit(function)], type_ignores=[])),
                     'six-queue', 'exec'), env)
        return env['wait_queue_capacity_frame'](seed), env, capture, ensure

    @staticmethod
    def frame(used, total, evidence='numeric', **kwargs):
        return SimpleNamespace(capacity=SimpleNamespace(used=used, total=total, evidence=evidence),
                               search=(90, 1754), **kwargs)

    def test_free_numeric_frame_is_reused_without_capture(self):
        frame = self.frame(4, 6)
        result, env, capture, _ = self.run_queue(frame)
        self.assertEqual(result, (frame, (90, 1754)))
        self.assertEqual(env['baseline_march_capacity'], (4, 6))
        capture.assert_not_called()

    def test_full_five_waits_for_a_new_free_frame(self):
        full, free = self.frame(5, 5), self.frame(4, 5)
        result, env, capture, _ = self.run_queue(full, [free])
        self.assertIs(result[0], free)
        self.assertEqual(env['baseline_march_capacity'], (4, 5))
        capture.assert_called_once()

    def test_limit_one_waits_when_one_of_five_or_six_is_occupied(self):
        for total in (5, 6):
            with self.subTest(total=total):
                occupied, empty = self.frame(1, total), self.frame(0, total)
                result, env, capture, _ = self.run_queue(occupied, [empty], limit=1)
                self.assertIs(result[0], empty)
                self.assertEqual(env['baseline_march_capacity'], (0, total))
                capture.assert_called_once()

    def test_limit_one_hidden_idle_does_not_guess_total(self):
        frame = self.frame(0, 0, 'hidden_idle')
        result, env, capture, _ = self.run_queue(frame, limit=1)
        self.assertIs(result[0], frame)
        self.assertEqual(env['baseline_march_capacity'], (0, 0))
        capture.assert_not_called()

    def test_hidden_idle_does_not_invent_capacity(self):
        frame = self.frame(0, 0, 'hidden_idle')
        result, env, capture, _ = self.run_queue(frame)
        self.assertIs(result[0], frame)
        self.assertEqual(env['baseline_march_capacity'], (0, 0))
        capture.assert_not_called()

    def test_unknown_capacity_cannot_authorize_search(self):
        frame = SimpleNamespace(capacity=None, search=(90, 1754))
        result, _, capture, _ = self.run_queue(frame, pause=lambda: True)
        self.assertIsNone(result)
        capture.assert_not_called()

    def test_panel_change_discards_seed_before_search(self):
        stale = self.frame(4, 6, expanded=True)
        fresh = self.frame(5, 6)
        result, env, capture, ensure = self.run_queue(stale, [fresh])
        self.assertIs(result[0], fresh)
        self.assertEqual(env['baseline_march_capacity'], (5, 6))
        ensure.assert_called_once()
        capture.assert_called_once()


if __name__ == '__main__':
    unittest.main()
