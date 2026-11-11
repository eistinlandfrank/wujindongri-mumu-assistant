"""Exercise the actual nested capacity gate with simulated fresh frames."""
import ast
import json
import tempfile
from enum import Enum
from pathlib import Path
from types import SimpleNamespace

class Resource(Enum):
    MEAT = 'meat'

DAILY_GATHER_REQUIRED_AMOUNTS = {Resource.MEAT: 50000}

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ((ROOT / 'wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8') + (Path(__file__).resolve().parents[1] / "wjdr_daily_controller.py").read_text(encoding="utf-8") + (Path(__file__).resolve().parents[1] / "wjdr_runtime_config.py").read_text(encoding="utf-8"))


def capacity_gate(frames, require_empty):
    tree = ast.parse(SOURCE)
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'confirm_daily_free_march_capacity')
    node.body = [n for n in node.body if not isinstance(n, ast.Nonlocal)]
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    now = [0.0]
    remaining = iter(frames)
    def screenshot():
        return next(remaining, None)
    class Stop:
        def is_set(self): return False
        def wait(self, seconds):
            now[0] += seconds
            return False
    def capacity(frame):
        if frame is None or frame == 'unknown': return None
        used, total = frame
        return SimpleNamespace(used=used, total=total, free=total-used)
    env = dict(time=SimpleNamespace(monotonic=lambda:now[0]),
               self=SimpleNamespace(stop_event=Stop(), _log_for_device=lambda *a:None),
               target=SimpleNamespace(device='test'), daily_screenshot=screenshot,
               match_reviewed_gather_search=lambda f: ((1, 1), 1) if f is not None else (None, 0),
               read_daily_march_capacity=capacity, daily_gather_march_is_active=lambda *a:False,
               threshold=0.8, interval=0, AUTOMATION_STEP_TIMEOUT_SECONDS=1,
               DAILY_RETRY_LOCK_MAX_SECONDS=30, set_state=lambda *a:None)
    exec(compile(module, '<capacity-gate>', 'exec'), env)
    return env['confirm_daily_free_march_capacity']('test', require_empty=require_empty)


def test_recheck_requires_two_fresh_explicit_empty_frames():
    assert capacity_gate([(0, 3), (0, 3)], True) is True
    assert capacity_gate([(0, 3), (1, 3), (1, 3)], True) is None
    assert capacity_gate(['unknown', 'unknown'], True) is False
    assert capacity_gate([(1, 3), (1, 3)], False) is True
    assert capacity_gate([(3, 3), (3, 3)], False) is None


def test_expired_owned_queue_survives_restart_and_midnight():
    tree = ast.parse(SOURCE)
    names = {'load_active_gather_deferrals', 'save_active_gather_deferrals', 'defer_gather_kind'}
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
    for node in nodes:
        node.body = [n for n in node.body if not isinstance(n, ast.Nonlocal)]
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    kind = next(iter(DAILY_GATHER_REQUIRED_AMOUNTS))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'gather.json'
        path.write_text(json.dumps({'date':'yesterday', 'retry_at':{kind.value:900},
                                    'natural_queue_kinds':[kind.value]}), encoding='utf-8')
        env = dict(json=json, time=SimpleNamespace(time=lambda:1000, monotonic=lambda:200),
                   gather_deferral_state_path=path, CONFIG_DIR=Path(directory),
                   donation_day='today', DAILY_GATHER_REQUIRED_AMOUNTS=DAILY_GATHER_REQUIRED_AMOUNTS,
                   DailyMissionKind=type(kind), DAILY_RETRY_LOCK_MAX_SECONDS=30,
                   active_gather_retry_epoch={}, deferred_gather_recheck_at={},
                   natural_gather_queue_kinds=set(), daily_gather_sent_kinds=set(),
                   self=SimpleNamespace(_log_for_device=lambda *a:None),
                   target=SimpleNamespace(device='test'))
        exec(compile(module, '<persisted-gather>', 'exec'), env)
        env['load_active_gather_deferrals']()
        assert kind in env['natural_gather_queue_kinds']
        assert env['deferred_gather_recheck_at'][kind] <= 200
        env['defer_gather_kind'](kind, 10)
        assert kind in env['natural_gather_queue_kinds']
        saved = json.loads(path.read_text(encoding='utf-8'))
        assert kind.value in saved['natural_queue_kinds']
        assert saved['retry_at'][kind.value] == 1010


def test_one_cart_is_saved_before_dispatch_and_no_queue_precheck():
    start = SOURCE.index('def run_gather_plan(')
    end = SOURCE.index('def set_daily_training_quantity_to_max', start)
    route = SOURCE[start:end]
    assert 'confirm_daily_free_march_capacity(' not in route
    assert 'if formation_status == "queue_full"' in route
    assert 'defer_gather_kind(kind, 10.0)' in route
    assert route.index('daily_gather_sent_kinds.add(kind)') < route.index('target.tap(*dispatch_point)')
    assert route.index('natural_queue=True') < route.index('target.tap(*dispatch_point)')
    assert 'record_active_gather_countdown(kind)' not in route
    assert '"sent_kinds": sorted(kind.value for kind in daily_gather_sent_kinds)' in SOURCE


if __name__ == '__main__':
    test_recheck_requires_two_fresh_explicit_empty_frames()
    test_expired_owned_queue_survives_restart_and_midnight()
    test_one_cart_is_saved_before_dispatch_and_no_queue_precheck()
    print('one-cart persistence and safety: PASS')
