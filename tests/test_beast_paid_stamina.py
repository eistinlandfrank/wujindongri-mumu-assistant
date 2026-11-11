import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from wjdr_backend import beast_stamina_paid_only_page
from wjdr_mumu_assistant_qt import beast_stamina_close_point, beast_close_paid_stamina_overlay, beast_wait_for_natural_stamina


class PaidVisualTests(unittest.TestCase):
    def test_exact_paid_page_and_damaged_anchors(self):
        image = Image.open(Path(__file__).parent / 'fixtures' / 'beast_paid_only_page.png').convert('RGB')
        self.assertTrue(beast_stamina_paid_only_page(image))
        self.assertEqual(beast_stamina_close_point(image), (1330, 270))
        for box in [(500,240,900,320),(145,960,250,1080), (1030,985,1280,1049)]:
            with self.subTest(box=box):
                damaged = image.copy(); ImageDraw.Draw(damaged).rectangle(box, fill=(0,0,0))
                self.assertFalse(beast_stamina_paid_only_page(damaged))
                self.assertIsNone(beast_stamina_close_point(damaged))
        damaged = image.copy(); ImageDraw.Draw(damaged).rectangle((1290,230,1370,310), fill=(0,0,0))
        self.assertTrue(beast_stamina_paid_only_page(damaged))
        self.assertIsNone(beast_stamina_close_point(damaged))


class PaidRecoveryTests(unittest.TestCase):
    def test_wait_is_bounded_interruptible_and_checks_world(self):
        waits, checks = [], []
        self.assertTrue(beast_wait_for_natural_stamina(lambda s: waits.append(s) or False,
                        lambda: checks.append(True) or True, lambda: False))
        self.assertEqual(waits, [30] * 10)
        self.assertEqual(len(checks), 10)
        waits.clear()
        self.assertFalse(beast_wait_for_natural_stamina(lambda s: waits.append(s) or len(waits) == 2,
                         lambda: True, lambda: False))
        self.assertEqual(waits, [30, 30])
        with self.assertRaises(ValueError):
            beast_wait_for_natural_stamina(lambda s: False, lambda: True, lambda: False, seconds=31)

    def run_case(self, *, first=None, second=None, entry='sent', reserved=False, frames=None, stopped=False):
        first = {'paid': True, 'close': (8, 9)} if first is None else first
        second = dict(first) if second is None else second
        ledger = {'entry': None if entry is None else {'mode': 'fast', 'phase': entry, 'id': 'tok'}}
        frames = iter(frames if frames is not None else [{'formation': (2, 3)}] * 2)
        events = []
        result = beast_close_paid_stamina_overlay(
            first, second, paid=lambda f: f.get('paid', False),
            close_point=lambda f: f.get('close'), stable=lambda a,b: bool(a and a==b),
            network=lambda f: f.get('network', False), pending=lambda: ledger['entry'],
            reserved=lambda: reserved, check_active=lambda: events.append('lease'),
            tap=lambda p: events.append(('tap',p)), capture=lambda: next(frames, {}),
            match_world=lambda f: f.get('world'), match_formation=lambda f: f.get('formation'),
            archive=lambda token: (events.append(('archive',token)), ledger.update(entry=None)),
            stopped=lambda: stopped)
        return result, events, ledger

    def test_sent_is_archived_only_after_close_and_known_page(self):
        result, events, ledger = self.run_case()
        self.assertEqual(result, 'formation')
        self.assertEqual([e for e in events if isinstance(e,tuple)], [('tap',(8,9)),('archive','tok')])
        self.assertIsNone(ledger['entry'])

    def test_new_popup_without_item_transaction_closes_once(self):
        result, events, ledger = self.run_case(entry=None)
        self.assertEqual(result, 'formation')
        self.assertEqual([e for e in events if isinstance(e,tuple)], [('tap',(8,9))])

    def test_unknown_or_prepared_never_closes_or_archives(self):
        for kwargs in ({'second': {}}, {'entry': 'prepared'}, {'reserved': True},
                       {'first': {'paid': True, 'close': (8,9), 'network': True}},
                       {'second': {'paid': True}}, {'stopped': True}):
            with self.subTest(kwargs=kwargs):
                result, events, ledger = self.run_case(**kwargs)
                self.assertFalse(result)
                self.assertFalse(any(isinstance(e,tuple) for e in events))
                self.assertIsNotNone(ledger['entry'])

    def test_unready_post_close_never_repeats_or_archives(self):
        result, events, ledger = self.run_case(frames=[{}] * 8)
        self.assertFalse(result)
        self.assertEqual([e for e in events if isinstance(e,tuple)], [('tap',(8,9))])
        self.assertEqual(ledger['entry']['phase'], 'sent')


if __name__ == '__main__':
    unittest.main()
