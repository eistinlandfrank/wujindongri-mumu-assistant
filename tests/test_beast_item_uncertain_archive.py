import json
import tempfile
import unittest
from pathlib import Path

from wjdr_backend import (archive_beast_stamina_fast_batch_uncertain,
                          begin_beast_stamina_fast_batch,
                          load_beast_stamina_item_pending,
                          update_beast_stamina_fast_batch)


class ItemUncertainArchiveTest(unittest.TestCase):
    def test_sent_archive_is_account_isolated_and_does_not_assert_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'item.json'
            first = begin_beast_stamina_fast_batch('account-a', path=path)
            second = begin_beast_stamina_fast_batch('account-b', path=path)
            update_beast_stamina_fast_batch('account-a', first, path=path)
            archive_beast_stamina_fast_batch_uncertain('account-a', first, path=path)
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertIsNone(load_beast_stamina_item_pending('account-a', path=path))
            self.assertEqual(load_beast_stamina_item_pending('account-b', path=path)['id'], second)
            self.assertEqual(data['uncertain_history'][0]['id'], first)
            self.assertEqual(data['uncertain_history'][0]['outcome'], 'unknown')

    def test_prepared_and_wrong_identity_or_token_are_not_archived(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'item.json'
            token = begin_beast_stamina_fast_batch('account-a', path=path)
            with self.assertRaises(ValueError):
                archive_beast_stamina_fast_batch_uncertain('account-a', token, path=path)
            update_beast_stamina_fast_batch('account-a', token, path=path)
            for account, wrong_token in [('account-b', token), ('account-a', 'wrong')]:
                with self.assertRaises(ValueError):
                    archive_beast_stamina_fast_batch_uncertain(account, wrong_token, path=path)
            self.assertEqual(load_beast_stamina_item_pending('account-a', path=path)['id'], token)


if __name__ == '__main__':
    unittest.main()
