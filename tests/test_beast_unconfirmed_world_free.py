import unittest
from types import SimpleNamespace

from wjdr_mumu_assistant_qt import beast_unconfirmed_world_free


class UnconfirmedWorldFreeTest(unittest.TestCase):
    def test_only_stable_known_world_with_real_free_slot_allows_new_search(self):
        first, second = object(), object()
        world = lambda frame: (90, 1754)
        network = lambda frame: False
        stable = lambda a, b: bool(a and a == b)
        free = SimpleNamespace(used=2, total=6)
        self.assertTrue(beast_unconfirmed_world_free(first, second, free, free, 6, world, network, stable))
        for a, b, limit, check_world, check_network in (
                (free, SimpleNamespace(used=3, total=6), 6, world, network),
                (SimpleNamespace(used=5, total=5), SimpleNamespace(used=5, total=5), 6, world, network),
                (free, free, 2, world, network),
                (SimpleNamespace(used=0, total=0), SimpleNamespace(used=0, total=0), 6, world, network),
                (free, free, 6, lambda frame: None, network),
                (free, free, 6, world, lambda frame: True)):
            self.assertFalse(beast_unconfirmed_world_free(first, second, a, b, limit, check_world, check_network, stable))


if __name__ == '__main__':
    unittest.main()
