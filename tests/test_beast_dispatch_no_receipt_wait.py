import ast
import unittest
from pathlib import Path


class DispatchNoReceiptWaitTest(unittest.TestCase):
    def test_live_cycle_does_not_call_dispatch_receipt_or_stamina_number_readers(self):
        tree = ast.parse(Path('wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8'))
        cycle = next(node for node in ast.walk(tree)
                     if isinstance(node, ast.FunctionDef) and node.name == 'run_one_cycle')
        calls = {node.func.id for node in ast.walk(cycle)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertNotIn('monitor_new_concurrent_rally', calls)
        self.assertNotIn('read_beast_rally_dispatch_stamina', calls)
        self.assertNotIn('read_beast_rally_dispatch_stamina_shortfall', calls)
        self.assertIn('archive_beast_rally_unconfirmed_reservation', calls)


if __name__ == '__main__':
    unittest.main()
