"""Contracts at the new frontend module boundaries, without game input."""
import builtins
from pathlib import Path
import symtable
import typing
import unittest
from unittest.mock import patch

import wjdr_daily_controller as daily
import wjdr_mumu_assistant_qt as frontend
import wjdr_ui_components as components


class FrontendModulesTest(unittest.TestCase):
    def test_daily_controller_resolves_all_runtime_globals(self):
        path = Path(daily.__file__)
        table = symtable.symtable(path.read_text(encoding='utf-8'), str(path), 'exec')
        controller = next(child for child in table.get_children() if child.get_name() == 'DailyController')
        method = next(child for child in controller.get_children() if child.get_name() == '_start_daily_rewards_flow')

        def referenced_globals(scope):
            names = {s.get_name() for s in scope.get_symbols() if s.is_global() and s.is_referenced()}
            for child in scope.get_children():
                names.update(referenced_globals(child))
            return names

        self.assertEqual(referenced_globals(method) - set(vars(daily)) - set(dir(builtins)), set())

    def test_frontend_keeps_existing_entry_and_widgets(self):
        self.assertIs(frontend.Card, components.Card)
        self.assertIs(frontend.ScreenshotView, components.ScreenshotView)
        self.assertIn('point', typing.get_type_hints(components.ScreenshotView._to_image))
        window = type('WindowStub', (), {'adb': None})()
        with patch.object(daily.QMessageBox, 'warning') as warning:
            frontend.MainWindow._start_daily_rewards_flow(window)
        warning.assert_called_once()


if __name__ == '__main__':
    unittest.main()
