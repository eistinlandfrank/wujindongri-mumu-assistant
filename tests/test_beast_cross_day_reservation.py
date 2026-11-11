import ast
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from wjdr_backend import (reserve_beast_rally_stamina,
                          load_beast_rally_stamina_reserved_any_day)


class CrossDayReservationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "ledger.json"
        self.identity = "mumu:2:android:two"

    def reserve(self, identity, day):
        return reserve_beast_rally_stamina(identity, 25, day=day, path=self.path)

    def test_previous_day_pending_is_preserved_and_other_account_is_independent(self):
        self.reserve(self.identity, "2026-11-03")
        self.assertEqual(load_beast_rally_stamina_reserved_any_day(self.identity, path=self.path), 25)
        self.assertEqual(load_beast_rally_stamina_reserved_any_day("mumu:5:android:five", path=self.path), 0)
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.reserve(self.identity, "2026-11-04")
        self.assertEqual(self.path.read_bytes(), before)
        self.reserve("mumu:5:android:five", "2026-11-04")
        data = json.loads(self.path.read_text(encoding="utf-8"))["accounts"]
        self.assertEqual(data[self.identity]["reserved"], 25)
        self.assertEqual(data[self.identity]["day"], "2026-11-03")
        self.assertEqual(data["mumu:5:android:five"]["reserved"], 25)

    def test_previous_day_cleared_record_rolls_over_and_second_reserve_fails(self):
        self.path.write_text(json.dumps({"accounts": {self.identity: {
            "day": "2026-11-03", "reserved": 0, "spent": 70}}}), encoding="utf-8")
        self.reserve(self.identity, "2026-11-04")
        before = self.path.read_bytes()
        account = json.loads(before)["accounts"][self.identity]
        self.assertEqual((account["day"], account["reserved"], account["spent"]),
                         ("2026-11-04", 25, 0))
        with self.assertRaises(ValueError):
            self.reserve(self.identity, "2026-11-04")
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_ledger_is_never_overwritten(self):
        for contents in (b"{", b"[]", b'{"accounts": []}',
                         b'{"accounts": {"mumu:2:android:two": null}}'):
            with self.subTest(contents=contents):
                self.path.write_bytes(contents)
                with self.assertRaises(ValueError):
                    self.reserve(self.identity, "2026-11-04")
                self.assertEqual(self.path.read_bytes(), contents)
                with self.assertRaises(ValueError):
                    load_beast_rally_stamina_reserved_any_day(self.identity, path=self.path)

    def test_invalid_pending_value_is_never_overwritten(self):
        for value in (-1, 1.5, True, None, "25"):
            with self.subTest(value=value):
                contents = json.dumps({"accounts": {self.identity: {
                    "day": "2026-11-03", "reserved": value}}}).encode()
                self.path.write_bytes(contents)
                with self.assertRaises(ValueError):
                    self.reserve(self.identity, "2026-11-04")
                self.assertEqual(self.path.read_bytes(), contents)
                with self.assertRaises(ValueError):
                    load_beast_rally_stamina_reserved_any_day(self.identity, path=self.path)


class StartupGuardTests(unittest.TestCase):
    def run_startup_guard(self, result, unresolved=False):
        source = Path(__file__).resolve().parents[1] / "wjdr_mumu_assistant_qt.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        flow = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == "_start_beast_rally_flow")
        job = next(node for node in flow.body if isinstance(node, ast.FunctionDef) and node.name == "job")
        # Execute the actual leading guard, with a sentinel representing all
        # subsequent work; no Qt or real device is involved.
        guard = ast.FunctionDef(name="guard", args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[],
                                      kw_defaults=[], defaults=[]),
                                body=job.body[:2] + [ast.parse("reached.append(reconciliation_only)").body[0]],
                                decorator_list=[])
        module = ast.fix_missing_locations(ast.Module(body=[guard], type_ignores=[]))
        logs, reached = [], []
        def loader(identity):
            if isinstance(result, Exception):
                raise result
            return result
        namespace = {"identity": "mumu:2:android:abc123", "target": SimpleNamespace(device="test"),
                     "self": SimpleNamespace(_log_for_device=lambda device, message: logs.append(message)),
                     "load_beast_rally_stamina_reserved_any_day": loader, "reached": reached}
        exec(compile(module, str(source), "exec"), namespace)
        from unittest.mock import patch
        with patch("wjdr_beast_supervision.has_unresolved_actions", return_value=unresolved):
            namespace["guard"]()
        return logs, reached

    def test_pending_or_unreadable_ledger_stops_before_subsequent_work(self):
        for result in (25, ValueError("damaged")):
            with self.subTest(result=result):
                logs, reached = self.run_startup_guard(result)
                self.assertTrue(logs)
                self.assertFalse(reached)
        self.assertEqual(self.run_startup_guard(0)[1], [False])
        self.assertEqual(self.run_startup_guard(0, unresolved=True)[1], [True])
        self.assertEqual(self.run_startup_guard(25, unresolved=True)[1], [True])


if __name__ == "__main__":
    unittest.main()
