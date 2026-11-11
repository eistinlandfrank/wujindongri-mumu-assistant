"""Exercise the guarded carousel recovery branch without sending game input."""
import ast
from pathlib import Path
import threading
import unittest


class SearchRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (Path(__file__).resolve().parents[1] / 'wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'configure_level')
        module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), node], type_ignores=[])
        cls.code = compile(ast.fix_missing_locations(module), '<search-recovery>', 'exec')

    def run_case(self, initial_visible, after_visible=None, after_confirmed=True):
        class Target:
            device = 'test'
            def __init__(self): self.swipes = []
            def shell(self, args, timeout): self.swipes.append(args)
        class Window:
            stop_event = threading.Event()
            def _log_for_device(self, *args): pass
        target = Target()
        calls = []
        def wait(_label, matcher):
            calls.append(matcher)
            if len(calls) == 1: return ('initial', None, None)
            if not initial_visible and len(calls) == 2:
                return ('after', None, None) if after_confirmed else None
            return None
        env = {
            'self': Window(), 'target': target, 'wait_for_double': wait,
            'match_beast_rally_search_drawer': object(), 'selector_match': object(),
            'beast_rally_beast_target_point': lambda image: (1, 1) if (initial_visible if image == 'initial' else after_visible) else None,
            'map_content_point': lambda point, size, image: point,
        }
        exec(self.code, env)
        self.assertIsNone(env['configure_level']())
        return target.swipes

    def test_missing_card_gets_left_then_confirmed_right_recovery(self):
        swipes = self.run_case(False, False)
        self.assertEqual([s[2:6] for s in swipes], [['1100', '1780', '400', '1780'], ['150', '1780', '1280', '1780']])

    def test_left_recheck_success_does_not_reverse(self):
        self.assertEqual(len(self.run_case(False, True)), 1)

    def test_unknown_page_stops_before_reverse(self):
        self.assertEqual(len(self.run_case(False, after_confirmed=False)), 1)

    def test_visible_card_does_not_swipe(self):
        self.assertEqual(self.run_case(True), [])
