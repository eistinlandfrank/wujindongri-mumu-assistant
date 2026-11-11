import unittest
from types import SimpleNamespace

from wjdr_backend import prune_runtime_evidence


class _File:
    def __init__(self, stamp, *, stat_error=None, unlink_error=None):
        self.stamp, self.stat_error, self.unlink_error = stamp, stat_error, unlink_error
        self.removed = False

    def stat(self):
        if self.stat_error:
            raise self.stat_error
        return SimpleNamespace(st_mtime=self.stamp)

    def unlink(self):
        if self.unlink_error:
            raise self.unlink_error
        self.removed = True


class EvidenceRaceTests(unittest.TestCase):
    def test_disappearing_and_open_files_do_not_stop_pruning(self):
        newest = _File(4)
        locked = _File(3, unlink_error=PermissionError())
        gone = _File(2, stat_error=FileNotFoundError())
        gone_before_unlink = _File(1, unlink_error=FileNotFoundError())
        oldest = _File(0)
        directory = SimpleNamespace(glob=lambda pattern: [newest, locked, gone, gone_before_unlink, oldest])
        self.assertEqual(prune_runtime_evidence(directory, 1), 1)
        self.assertFalse(newest.removed)
        self.assertTrue(oldest.removed)

    def test_unexpected_io_error_is_not_hidden(self):
        broken = _File(1, stat_error=OSError('disk error'))
        with self.assertRaises(OSError):
            prune_runtime_evidence(SimpleNamespace(glob=lambda pattern: [broken]), 1)


if __name__ == '__main__':
    unittest.main()
