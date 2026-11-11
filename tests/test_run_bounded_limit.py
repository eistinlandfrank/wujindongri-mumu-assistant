"""Fast focused verification of hard watchdog limits."""
import subprocess, sys, unittest
from pathlib import Path
RUN = Path(__file__).resolve().parents[1] / 'scripts/run_bounded.py'

class BoundTests(unittest.TestCase):
    def invoke(self, seconds, code):
        return subprocess.run([sys.executable,str(RUN),'--seconds',str(seconds),sys.executable,'-c',code],capture_output=True,timeout=5)
    def test_reject_long_limit(self):
        self.assertEqual(self.invoke(31,'print("should not start")').returncode,2)
    def test_normal(self):
        self.assertEqual(self.invoke(2,'pass').returncode,0)
    def test_timeout(self):
        self.assertEqual(self.invoke(.1,'import time; time.sleep(10)').returncode,124)

if __name__=='__main__':unittest.main()
