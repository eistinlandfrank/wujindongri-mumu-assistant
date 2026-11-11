"""Unconfirmed dispatch recovery is accounting, never a dispatch receipt."""
import ast
import tempfile
import threading
import unittest
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from wjdr_backend import (DailyMarchCapacity, reserve_beast_rally_stamina,
                          reconcile_beast_rally_idle_reservation,
                          load_beast_rally_stamina_reserved,
                          load_beast_rally_stamina_uncertain)


def make_helper(reconcile, *, stopped=False, target=None):
    tree = ast.parse(Path('wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8'))
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
              and n.name == 'reconcile_unconfirmed_hidden_idle')
    class Bind(ast.NodeTransformer):
        def visit_Nonlocal(self, node):
            return ast.copy_location(ast.Global(names=node.names), node)
    event = threading.Event()
    if stopped:
        event.set()
    env = dict(idle_reconcile_failure_reported=False, identity='test-account', threshold=.9,
               self=SimpleNamespace(stop_event=event, _log_for_device=Mock()),
               target=target or SimpleNamespace(device='test', check_active=Mock()),
               read_beast_rally_collapsed_march_capacity=lambda frame, _: frame,
               reconcile_beast_rally_idle_reservation=reconcile, set_state=Mock())
    exec(compile(ast.fix_missing_locations(ast.Module(body=[Bind().visit(fn)], type_ignores=[])),
                 'hidden_idle_reconcile', 'exec'), env)
    return env['reconcile_unconfirmed_hidden_idle'], env


class HiddenIdleReconcileTest(unittest.TestCase):
    def test_actual_ledger_transfers_only_selected_account_to_uncertain(self):
        with tempfile.TemporaryDirectory() as folder:
            opts = dict(path=Path(folder) / 'ledger.json', day='2026-11-04')
            reserve_beast_rally_stamina('test-account', 25, **opts)
            reserve_beast_rally_stamina('other-account', 20, **opts)
            helper, env = make_helper(partial(reconcile_beast_rally_idle_reservation, **opts))
            idle = DailyMarchCapacity(0, 0, .99, 'hidden_idle')
            self.assertTrue(helper(idle, idle))
            self.assertEqual(load_beast_rally_stamina_reserved('test-account', **opts), 0)
            self.assertEqual(load_beast_rally_stamina_uncertain('test-account', **opts), 25)
            self.assertEqual(load_beast_rally_stamina_reserved('other-account', **opts), 20)
            env['target'].check_active.assert_called_once()

    def test_unknown_mismatched_numeric_and_stopped_never_reconcile(self):
        idle = DailyMarchCapacity(0, 0, .99, 'hidden_idle')
        numeric = DailyMarchCapacity(0, 6, .99)
        active = DailyMarchCapacity(1, 6, .99)
        for first, second in [(None, idle), (idle, None), (idle, numeric),
                              (numeric, numeric), (idle, active)]:
            reconcile = Mock(return_value=25)
            helper, _ = make_helper(reconcile)
            self.assertFalse(helper(first, second))
            reconcile.assert_not_called()
        reconcile = Mock(return_value=25)
        helper, _ = make_helper(reconcile, stopped=True)
        self.assertFalse(helper(idle, idle))
        reconcile.assert_not_called()

    def test_unavailable_current_day_or_lost_lease_blocks_recovery(self):
        idle = DailyMarchCapacity(0, 0, .99, 'hidden_idle')
        helper, env = make_helper(Mock(return_value=0))
        self.assertFalse(helper(idle, idle))
        self.assertFalse(helper(idle, idle))
        self.assertEqual(env['self']._log_for_device.call_count, 1)
        target = SimpleNamespace(device='test', check_active=Mock(side_effect=InterruptedError()))
        reconcile = Mock()
        helper, _ = make_helper(reconcile, target=target)
        with self.assertRaises(InterruptedError):
            helper(idle, idle)
        reconcile.assert_not_called()

    def test_real_cross_day_reservation_stays_reserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ledger.json'
            reserve_beast_rally_stamina('test-account', 25, path=path, day='2026-11-03')
            helper, _ = make_helper(partial(reconcile_beast_rally_idle_reservation,
                                             path=path, day='2026-11-04'))
            idle = DailyMarchCapacity(0, 0, .99, 'hidden_idle')
            self.assertFalse(helper(idle, idle))
            self.assertEqual(load_beast_rally_stamina_reserved('test-account', path=path,
                                                               day='2026-11-03'), 25)


if __name__ == '__main__':
    unittest.main()
