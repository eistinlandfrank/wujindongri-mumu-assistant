import tempfile
import unittest
import zipfile
from pathlib import Path

import wjdr_scoreboard as s

ACCOUNT = 'mumu:2:android:abc123'
OTHER = 'mumu:0:android:abc123'


def row(rank, country, alliance, name, score):
    return dict(rank=rank, country=country, alliance=alliance, name=name, score=score)


class ScoreboardTest(unittest.TestCase):
    def test_imports_workbook_and_ignores_formula(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.xlsx'
            sheet = '''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
            <row r="1"><c r="A1"><v>1</v></c><c r="B1" t="inlineStr"><is><t>#523</t></is></c>
            <c r="C1" t="inlineStr"><is><t>RMB</t></is></c><c r="D1" t="inlineStr"><is><t>测试</t></is></c><c r="E1"><v>12345</v></c></row>
            <row r="2"><c r="A2"><v>2</v></c><c r="D2" t="inlineStr"><is><t>忽略</t></is></c><c r="E2"><f>1+1</f><v>2</v></c></row>
            </sheetData></worksheet>'''
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('xl/worksheets/sheet1.xml', sheet)
            rows = s.read_xlsx(path)
            self.assertEqual(rows, [row(1, '#523', 'RMB', '测试', 12345)])

    def test_scoped_storage_and_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = s.save_snapshot(ACCOUNT, [row(1, '#523', 'OLD', '甲', 100), row(2, '#700', 'A', '乙', 50)], 'first', root)
            b = s.save_snapshot(ACCOUNT, [row(2, '#523', 'NEW', '甲', 125), row(1, '#700', 'A', '乙', 90)], 'latest', root)
            self.assertEqual(s.load_snapshots(ACCOUNT, root)[0]['id'], a['id'])
            self.assertEqual(s.load_snapshots(OTHER, root), [])
            result = s.compare_snapshots(a, b)
            self.assertEqual([item['delta'] for item in result['changed']], [40, 25])
            self.assertEqual(result['changed'][1]['new']['alliance'], 'NEW')
            self.assertEqual(result['unmatched_new'], [])
            with self.assertRaises(ValueError):
                s.compare_snapshots(a, dict(b, identity=OTHER))

    def test_ambiguous_or_unknown_never_guesses(self):
        old = {'identity': ACCOUNT, 'rows': [row(1, '#523', 'A', '同名', 10), row(2, '#523', 'B', '同名', 20), row(3, '', '', '未知', 1)]}
        new = {'identity': ACCOUNT, 'rows': [row(1, '#523', 'A', '同名', 30), row(2, '', '', '未知', 3)]}
        result = s.compare_snapshots(old, new)
        self.assertEqual(result['changed'], [])
        self.assertEqual((len(result['unmatched_old']), len(result['unmatched_new'])), (3, 2))

    def test_duplicate_ranks_rejected(self):
        with self.assertRaises(ValueError):
            s.validate_rows([row(1, '#523', '', '甲', 1), row(1, '#523', '', '乙', 2)])

    def test_multiple_capture_drafts_remain_available_per_account(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            s.save_capture_draft(ACCOUNT, [row(1, '#523', 'A', '甲', 1)], 'a' * 32, root)
            s.save_capture_draft(ACCOUNT, [row(1, '#523', 'A', '甲', 1), row(2, '#523', 'B', '乙', 2)], 'b' * 32, root)
            s.save_capture_draft(OTHER, [row(1, '#700', '', '丙', 3)], 'c' * 32, root)
            drafts = s.list_capture_drafts(ACCOUNT, root)
            self.assertEqual({(d['id'], len(d['rows'])) for d in drafts}, {('a' * 32, 1), ('b' * 32, 2)})
            self.assertEqual(len(s.list_capture_drafts(OTHER, root)), 1)

    def test_rank_progress_requires_no_gap_and_forward_motion(self):
        self.assertTrue(s.ranks_advance([4, 5, 6, 7], [7, 8, 9]))
        self.assertTrue(s.ranks_advance([4, 5, 6, 7], [8, 9, 10]))
        self.assertFalse(s.ranks_advance([4, 5, 6, 7], [9, 10]))
        self.assertFalse(s.ranks_advance([4, 5, 6, 7], [4, 5, 6, 7]))
        self.assertFalse(s.ranks_advance([4, 5, 6, 7], [8, 8, 9]))
        self.assertFalse(s.ranks_advance([4, 5, 6, 7], [8, 10]))

    def test_rank_ocr_disagreement_is_not_silently_accepted(self):
        badges = [{'words': [{'text': '18', 'x': 200, 'y': 1100}]}]
        tiles = [{'words': [{'text': '78', 'x': 60, 'y': 20}]}]
        result = s.merge_rank_ocr(badges, tiles, [1100])
        self.assertEqual(result[0]['words'], [])
        tiles[0]['words'][0]['text'] = '18'
        result = s.merge_rank_ocr(badges, tiles, [1100])
        self.assertEqual(result[0]['words'][0]['text'], '18')

    def test_two_hundred_rows_and_signed_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = [row(i, '#523' if i % 2 else '#700', 'A', f'player{i}', 10000) for i in range(1, 201)]
            new = [dict(r, score=r['score'] + (r['rank'] - 100), alliance='B') for r in old]
            first = s.save_snapshot(ACCOUNT, old, 'first', root)
            latest = s.save_snapshot(ACCOUNT, new, 'latest', root)
            self.assertTrue(first['complete'] and latest['complete'])
            result = s.compare_snapshots(first, latest)
            self.assertEqual([r['delta'] for r in result['changed']], list(range(100, 0, -1)) + list(range(-1, -100, -1)))
            self.assertFalse(result['unmatched_old'] or result['unmatched_new'])

    def test_missing_name_retries_only_visible_score_rows(self):
        score = {'words': [{'x': 536, 'y': 1471, 'text': '114'}, {'x': 600, 'y': 1497, 'text': '，'},
                           {'x': 611, 'y': 1471, 'text': '335'}, {'x': 693, 'y': 1496, 'text': '，'},
                           {'x': 704, 'y': 1471, 'text': '108'}]}
        self.assertEqual(s.missing_name_score_positions([score]), [1471])
        name = {'words': [{'x': 700, 'y': 1390, 'text': '昵称'}]}
        self.assertEqual(s.missing_name_score_positions([score, name]), [])

    def test_retried_rows_are_ordered_and_country_uses_same_row(self):
        def line(text, x, y):
            return {'text': text, 'words': [{'text': text, 'x': x, 'y': y}]}
        lines = [line('个人积分排名备战阶段', 500, 200),
                 line('#700', 540, 1220), line('[A]甲', 700, 1220),
                 line('#523', 540, 1490), line('[B]乙', 700, 1490),
                 line('90,000,000', 536, 1570), line('100,000,000', 536, 1300)]
        badges = [{'words': [{'text': '2', 'x': 200, 'y': 1510}, {'text': '1', 'x': 200, 'y': 1240}]}]
        rows = s.candidate_rows(lines, badges)
        self.assertEqual([(r['rank'], r['country']) for r in rows], [('1', '#700'), ('2', '#523')])

    def test_ocr_deskew_coordinates_restore_original_location(self):
        lines = [{'angle': -5.2, 'words': [{'text': '11', 'x': 187, 'y': 1381}]}]
        word = s.restore_ocr_coordinates(lines, 1440, 2560)[0]['words'][0]
        self.assertAlmostEqual(word['x'], 198.4, delta=1)
        self.assertAlmostEqual(word['y'], 1428.9, delta=1)

    def test_score_missing_comma_keeps_digit_groups(self):
        words = [{'x': x, 'text': text} for x, text in [(530, '136'), (600, '，'), (620, '205'), (700, '475')]]
        self.assertEqual(s.score_line_value({'words': words}), 136205475)
        words[-1]['text'] = '47'
        self.assertIsNone(s.score_line_value({'words': words}))


if __name__ == '__main__':
    unittest.main()
