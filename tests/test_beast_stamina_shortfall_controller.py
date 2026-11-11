"""Shortfall handling must not spend items without a durable receipt."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


class StaminaShortfallControllerTest(unittest.TestCase):
    def run_branch(self, first=25, second=25, cost=None, allowed=True, state='formation'):
        tree = ast.parse(Path('wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8'))
        branch = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                      and 'red_cost in (20, 25)' in ast.unparse(n.test))
        function = ast.FunctionDef(name='run', args=ast.arguments(posonlyargs=[], args=[],
            kwonlyargs=[], kw_defaults=[], defaults=[]), body=[branch, ast.Return(ast.Constant(True))],
            decorator_list=[])
        target = SimpleNamespace(device='device', tap=Mock(), back=Mock())
        log = Mock()
        limit = Mock(return_value=allowed)
        env = dict(red_cost=first, second_red_cost=second, cost=cost,
                   second_match=SimpleNamespace(state=state, point=(1, 2)),
                   BeastRallyState=SimpleNamespace(FORMATION='formation'),
                   dispatch=(1, 2), stable=lambda a, b: a == b,
                   identity='account', profile=SimpleNamespace(stamina_limit=250),
                   load_beast_rally_stamina_spent=lambda _: 200,
                   load_beast_rally_stamina_reserved=lambda _: 0,
                   load_beast_rally_stamina_uncertain=lambda _: 25,
                   beast_rally_stamina_limit_allows=limit,
                   target=target, self=SimpleNamespace(_log_for_device=log), set_state=Mock())
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                     'shortfall', 'exec'), env)
        result = env['run']()
        target.tap.assert_not_called()
        target.back.assert_not_called()
        return result, env, log, limit

    def test_known_costs_pause_without_item_or_dispatch(self):
        for cost in (20, 25):
            with self.subTest(cost=cost):
                result, env, log, limit = self.run_branch(first=cost, second=cost)
                self.assertFalse(result)
                limit.assert_called_once_with(225, cost, 250)
                self.assertIn('未自动使用道具', log.call_args.args[1])
                self.assertIn(str(cost), log.call_args.args[1])
                env['set_state'].assert_called_once()

    def test_actual_cost_is_used_for_limit(self):
        result, _, log, limit = self.run_branch(allowed=False)
        self.assertFalse(result)
        limit.assert_called_once_with(225, 25, 250)
        self.assertIn('25', log.call_args.args[1])
        self.assertIn('未打开', log.call_args.args[1])

    def test_unmatched_or_unproven_frames_do_not_enter_branch(self):
        for values in (dict(first=25, second=20), dict(first=25, second=None),
                       dict(first=None, second=None), dict(first=30, second=30),
                       dict(cost=25), dict(state='unknown')):
            with self.subTest(values=values):
                result, _, log, limit = self.run_branch(**values)
                self.assertTrue(result)
                log.assert_not_called()
                limit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
