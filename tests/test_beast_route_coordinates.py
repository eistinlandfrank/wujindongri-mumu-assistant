import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import wjdr_beast_hunt as hunt


class BeastRouteCoordinatesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.identity = 'mumu:5:android:abc123'
        self.image = SimpleNamespace(size=(1440, 2560))
        self.viewport = (0, 0, 1440, 2560)
        self.positions = hunt.CycleActionPositions()
        for i, name in enumerate(hunt._ROUTE_COORDINATE_NAMES, 1):
            self.positions.positions[name] = (self.image.size, self.viewport, (i * 50, i * 100), 'not saved', 'pixels')
        self.viewport_patch = patch.object(hunt, 'content_viewport', return_value=SimpleNamespace(box=self.viewport))
        self.viewport_patch.start()
        self.addCleanup(self.viewport_patch.stop)

    def save(self, **kwargs):
        return hunt.save_beast_route_coordinates(self.identity, 8, self.positions, False,
                                                 directory=self.directory.name, **kwargs)

    def load(self, identity=None, level=8, image=None):
        result = hunt.CycleActionPositions()
        flag = hunt.load_beast_route_coordinates(identity or self.identity, level, image or self.image,
                                                  result, directory=self.directory.name)
        return flag, result

    def test_roundtrip_only_coordinates_and_same_identity_and_geometry(self):
        self.assertTrue(self.save())
        path = hunt._beast_route_path(self.identity, self.directory.name)
        payload = json.loads(path.read_text(encoding='utf-8'))
        self.assertNotIn('pixels', path.read_text(encoding='utf-8'))
        self.assertNotIn(self.identity, path.read_text(encoding='utf-8'))
        flag, loaded = self.load()
        self.assertIs(flag, False)
        self.assertEqual(loaded.cached_point('launch', self.image), self.positions.positions['launch'][2])
        self.assertIsNone(loaded.reuse('launch', self.image))
        self.assertEqual(payload['mode'], 'manual')
        self.assertIsNone(self.load(level=9)[0])
        self.assertIsNone(self.load(image=SimpleNamespace(size=(720, 1280)))[0])
        other = 'mumu:6:android:abc123'
        hunt._beast_route_path(other, self.directory.name).write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
        self.assertIsNone(self.load(identity=other)[0])

    def test_old_corrupt_or_incomplete_file_is_ignored(self):
        self.assertTrue(self.save())
        path = hunt._beast_route_path(self.identity, self.directory.name)
        valid = json.loads(path.read_text(encoding='utf-8'))
        for bad in ('not json', json.dumps({'version': 0}),
                    json.dumps({**valid, 'points': {}}),
                    json.dumps({**valid, 'points': {**valid['points'], 'launch': [9999, 0]}})):
            path.write_text(bad, encoding='utf-8')
            flag, result = self.load()
            self.assertIsNone(flag)
            self.assertEqual(result.positions, {})

    def test_failed_atomic_replace_keeps_prior_valid_file(self):
        self.assertTrue(self.save())
        path = hunt._beast_route_path(self.identity, self.directory.name)
        before = path.read_bytes()
        with patch.object(hunt.os, 'replace', side_effect=OSError('failure')):
            with self.assertRaises(OSError):
                self.save()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(Path(self.directory.name).glob('*.tmp')), [])

    def test_incomplete_identity_and_missing_points_never_persist(self):
        self.assertFalse(hunt.save_beast_route_coordinates('mumu:5', 8, self.positions, False,
                                                           directory=self.directory.name))
        del self.positions.positions['launch']
        self.assertFalse(self.save())
        self.assertFalse(list(Path(self.directory.name).glob('*.json')))


if __name__ == '__main__':
    unittest.main()
