"""Crash-safe item-use journaling; observations are not OCR verification."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from wjdr_backend import (begin_beast_stamina_item_use, confirm_beast_stamina_item_use,
                          load_beast_stamina_item_pending)


class BeastItemTransactionTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'items.json'

    def begin(self, identity='index2/android-id', observation=(876, 16)):
        return begin_beast_stamina_item_use(identity, observation, observation, path=self.path)

    def test_confirmed_use_requires_both_inventory_and_stamina(self):
        token = self.begin()
        for first, second in [((876, 28), (876, 28)), ((875, 16), (875, 16)),
                              ((874, 38), (874, 38)), ((875, 28), (875, 29)),
                              (None, None)]:
            self.assertFalse(confirm_beast_stamina_item_use('index2/android-id', token, first, second, path=self.path))
            self.assertEqual(load_beast_stamina_item_pending('index2/android-id', path=self.path)['id'], token)
        self.assertTrue(confirm_beast_stamina_item_use('index2/android-id', token, (875, 28), (875, 28), path=self.path))
        self.assertIsNone(load_beast_stamina_item_pending('index2/android-id', path=self.path))
        self.begin(observation=(875, 28))

    def test_natural_stamina_recovery_after_use(self):
        token = self.begin(observation=(1407, 0))
        self.assertFalse(confirm_beast_stamina_item_use('index2/android-id', token, (1406, 10), (1406, 11), path=self.path))
        self.assertTrue(confirm_beast_stamina_item_use('index2/android-id', token, (1406, 11), (1406, 11), path=self.path))
        self.assertIsNone(load_beast_stamina_item_pending('index2/android-id', path=self.path))
        with self.assertRaises(ValueError):
            confirm_beast_stamina_item_use('index2/android-id', token, (1406, 11), (1406, 11), path=self.path)

    def test_reopen_and_other_day_do_not_clear_pending(self):
        token = self.begin()
        raw = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(raw['accounts']['index2/android-id']['id'], token)
        with self.assertRaises(ValueError):
            self.begin()
        other = self.begin(identity='index3/other')
        self.assertNotEqual(token, other)
        with self.assertRaises(ValueError):
            confirm_beast_stamina_item_use('index2/android-id', other, (875, 28), (875, 28), path=self.path)

    def test_new_process_and_next_day_keep_unresolved_use(self):
        token = self.begin()
        script = '''
from pathlib import Path
from unittest.mock import patch
import sys
import wjdr_backend as b
path = Path(sys.argv[1])
with patch.object(b, "_beast_rally_ledger_day", return_value="2099-01-01"):
    assert b.load_beast_stamina_item_pending("index2/android-id", path=path)["id"] == sys.argv[2]
    try:
        b.begin_beast_stamina_item_use("index2/android-id", (876, 16), (876, 16), path=path)
    except ValueError:
        pass
    else:
        raise AssertionError("unresolved item input allowed a second use")
'''
        result = subprocess.run([sys.executable, '-c', script, str(self.path), token],
                                capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(load_beast_stamina_item_pending('index2/android-id', path=self.path)['id'], token)

    def test_bad_input_or_corrupt_ledger_fails_closed(self):
        for first, second in [((0, 16), (0, 16)), ((True, 16), (1, 16)),
                              ((876, 16), (876, 17)), (None, None)]:
            with self.assertRaises(ValueError):
                begin_beast_stamina_item_use('id', first, second, path=self.path)
        self.path.write_text('{corrupt', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.begin()
        with self.assertRaises(ValueError):
            load_beast_stamina_item_pending('id', path=self.path)


if __name__ == '__main__':
    unittest.main()
