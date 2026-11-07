import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QWidget

import wjdr_scoreboard as scores
from wjdr_scoreboard_ui import ScoreboardUI


class Page(QWidget, ScoreboardUI):
    def _score_identity(self):
        return 'mumu:2:android:abcd'


class BackgroundPageTest(unittest.TestCase):
    def test_recover_unreviewed_draft_in_background(self):
        app = QApplication.instance() or QApplication([])
        page = Page()
        widget = page._build_scoreboard_page()
        rows = [dict(rank=i, country='#523', alliance='RMB', name=f'测试{i}', score=i * 100)
                for i in range(1, 201)]
        with patch.object(scores, 'list_capture_drafts', return_value=[{'rows': rows}]):
            page._score_recover_draft()
        self.assertEqual(page.score_table.rowCount(), 200)
        self.assertTrue(page.score_has_unreviewed_ocr)
        self.assertEqual(page.score_editor_identity, 'mumu:2:android:abcd')
        widget.close()
        page.close()
        app.processEvents()

    def test_choose_older_complete_draft(self):
        app = QApplication.instance() or QApplication([])
        page = Page()
        widget = page._build_scoreboard_page()
        rows = [dict(rank=i, country='#523', alliance='', name=f'测试{i}', score=i)
                for i in range(1, 201)]
        drafts = [{'id': 'a' * 32, 'modified': 2, 'rows': rows[:1]},
                  {'id': 'b' * 32, 'modified': 1, 'rows': rows}]
        with patch.object(scores, 'list_capture_drafts', return_value=drafts), \
             patch('wjdr_scoreboard_ui.QInputDialog.getItem', side_effect=lambda *args: (args[3][1], True)):
            page._score_recover_draft()
        self.assertEqual(page.score_table.rowCount(), 200)
        self.assertTrue(page.score_has_unreviewed_ocr)
        widget.close()
        page.close()
        app.processEvents()


if __name__ == '__main__':
    unittest.main()
