"""Run a command with a <=300s deadline and kill its process tree on timeout."""
import argparse
import subprocess
import sys

p=argparse.ArgumentParser()
p.add_argument('--seconds',type=float,default=25)
p.add_argument('command',nargs=argparse.REMAINDER)
a=p.parse_args()
if not 0<a.seconds<=300 or not a.command:
    p.error('require command and 0 < seconds <= 300')
child=subprocess.Popen(a.command)
try:
    raise SystemExit(child.wait(timeout=a.seconds))
except subprocess.TimeoutExpired:
    subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],timeout=1.5,capture_output=True)
    print('HARD TIMEOUT: process tree terminated',file=sys.stderr)
    raise SystemExit(124)
