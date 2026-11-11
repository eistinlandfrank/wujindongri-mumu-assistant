"""Persistent user intent for future Beast supervision.

This module does not register accounts or send device input by itself. A
caller must hold the account's DeviceLease and recheck both the intent
generation and all pending transactions before issuing input. Until desktop
start/stop paths use this journal, absence of a record is unknown, not RUN.
"""

from __future__ import annotations

import json
import hashlib
import queue
import re
import threading
from pathlib import Path
from typing import Any

from wjdr_backend import (CONFIG_DIR, BEAST_RALLY_STAMINA_LEDGER_FILE,
                          BEAST_RALLY_ITEM_TRANSACTION_FILE,
                          load_beast_stamina_item_pending,
                          _durable_beast_item_write, _serialized_account_write)

SUPERVISION_FILE = CONFIG_DIR / "beast_supervision_intent.json"
_IDENTITY = re.compile(r"mumu:[0-9]+:android:[0-9a-f]+\Z")


class InitialRecognitionTimeout(RuntimeError):
    """A page could not be recognized before any device input was attempted."""


def run_preinput_recovery(job, target, stop_event, identity, generation,
                          verify_identity, report):
    """Retry only known pre-input failures while the caller retains its lease.

    The target's input-attempted flag is a lifetime latch, set before transport.
    A changed or stopped intent, pending transaction, or changed identity ends
    recovery without performing another game operation.
    """
    from wjdr_backend import AdbError

    while not stop_event.is_set():
        try:
            return job()
        except (AdbError, InitialRecognitionTimeout) as exc:
            if stop_event.is_set():
                return
            if target.input_attempted:
                raise
            is_timeout = isinstance(exc, InitialRecognitionTimeout)
            report("输入前页面识别超时，保留租约并重新核验账号。" if is_timeout
                   else "输入前 ADB 读取失败，保留租约并稍后重新核验账号。")
            if stop_event.wait(0.2 if is_timeout else 2.0):
                return
            while not stop_event.is_set():
                if (not token_matches(read_intent(identity), generation)
                        or has_unresolved_actions(identity)):
                    return
                try:
                    identity_status = verify_identity()
                except AdbError:
                    identity_status = None
                if identity_status is True:
                    break
                if identity_status is False:
                    report("账号身份已变化，停止恢复。")
                    return
                report("账号身份暂时无法核实，保留租约并等待，期间不执行游戏操作。")
                if stop_event.wait(2.0):
                    return


def _valid_identity(identity: str) -> bool:
    return isinstance(identity, str) and bool(_IDENTITY.fullmatch(identity))


def verify_bound_identity(adb, device: str, expected_identity: str) -> bool | None:
    """True on match, False on definite mismatch, None when unreadable.

    Callers may only input on True. Startup callers treating None as false
    remain fail-closed; pre-input recovery can retry an unreadable identity.
    """
    if not _valid_identity(expected_identity):
        return False
    fresh = adb.clone_for_device(device)
    fresh.device_identities.clear()
    fresh.device_boot_ids.clear()
    fresh.players = fresh._manager_players()
    if not fresh.players:
        return None
    actual = fresh.device_identity(device)
    if not _valid_identity(actual):
        return None
    return actual == expected_identity


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": 1, "accounts": {}}
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("accounts"), dict):
        raise ValueError("invalid supervision journal; preserve and stop")
    for key, record in data["accounts"].items():
        if (not _valid_identity(key) or not isinstance(record, dict)
                or type(record.get("generation")) is not int or record["generation"] < 1
                or type(record.get("run")) is not bool):
            raise ValueError("invalid supervision intent; preserve and stop")
    return data


@_serialized_account_write
def read_intent(identity: str, *, path: Path = SUPERVISION_FILE) -> dict[str, Any] | None:
    if not _valid_identity(identity):
        raise ValueError("complete stable MuMu identity required")
    record = _load(path)["accounts"].get(identity)
    return dict(record) if record is not None else None


@_serialized_account_write
def _set_intent_locked(identity: str, run: bool, *, path: Path = SUPERVISION_FILE) -> dict[str, Any]:
    """Persist an explicit user start/stop intent and invalidate older tokens."""
    if not _valid_identity(identity) or type(run) is not bool:
        raise ValueError("complete identity and explicit boolean intent required")
    data = _load(path)
    old = data["accounts"].get(identity)
    record = {"generation": (old["generation"] if old else 0) + 1, "run": run}
    data["accounts"][identity] = record
    _durable_beast_item_write(path, data)
    return dict(record)


def _account_lock_path(identity: str, path: Path) -> Path:
    if not _valid_identity(identity):
        raise ValueError("complete stable MuMu identity required")
    digest = hashlib.sha256(identity.encode("ascii")).hexdigest()
    return path.with_name(path.name + ".account." + digest)


@_serialized_account_write
def _under_account_lock(operation, *, path: Path):
    return operation()


def set_intent(identity: str, run: bool, *, path: Path = SUPERVISION_FILE) -> dict[str, Any]:
    """Serialize a stop or start against this account's guarded input."""
    return _under_account_lock(lambda: _set_intent_locked(identity, run, path=path),
                               path=_account_lock_path(identity, path))


def perform_if_current(identity: str, generation: int, operation, *, path: Path = SUPERVISION_FILE):
    """Run one input only while its explicit intent is still current.

    A successful stop uses the same per-account lock, so after the stop is
    persisted no old generation can submit another input.  Input exceptions
    are propagated and the caller must never replay an unknown acknowledgement.
    """
    def checked():
        if not token_matches(read_intent(identity, path=path), generation):
            raise InterruptedError("监督意图已停止或变化；未发送输入")
        return operation()
    return _under_account_lock(checked, path=_account_lock_path(identity, path))


@_serialized_account_write
def _start_if_unchanged_locked(identity: str, expected_generation: int | None, *, path: Path = SUPERVISION_FILE) -> dict[str, Any] | None:
    """Register a manual start only if no stop/start occurred during setup.

    ``None`` means the account had no prior record.  This compare-and-swap
    must be called after acquiring the account lease, never by a restart.
    """
    if not _valid_identity(identity) or (expected_generation is not None and
                                         (type(expected_generation) is not int or expected_generation < 1)):
        raise ValueError("invalid identity or generation")
    data = _load(path)
    old = data["accounts"].get(identity)
    current_generation = old["generation"] if old else None
    if current_generation != expected_generation:
        return None
    record = {"generation": (current_generation or 0) + 1, "run": True}
    data["accounts"][identity] = record
    _durable_beast_item_write(path, data)
    return dict(record)


def start_if_unchanged(identity: str, expected_generation: int | None, *, path: Path = SUPERVISION_FILE) -> dict[str, Any] | None:
    return _under_account_lock(
        lambda: _start_if_unchanged_locked(identity, expected_generation, path=path),
        path=_account_lock_path(identity, path),
    )


def stop_if_current(identity: str, generation: int, *, path: Path = SUPERVISION_FILE) -> bool:
    """Cancel only this worker's generation, never a later manual start."""
    def cancel():
        if not token_matches(read_intent(identity, path=path), generation):
            return False
        _set_intent_locked(identity, False, path=path)
        return True
    return _under_account_lock(cancel, path=_account_lock_path(identity, path))


def token_matches(record: dict[str, Any] | None, generation: int) -> bool:
    """Test a fresh journal read; this alone never authorizes a game action."""
    return (isinstance(record, dict) and record.get("run") is True
            and type(generation) is int and generation > 0
            and type(record.get("generation")) is int
            and record["generation"] == generation)


def has_unresolved_actions(identity: str, *, stamina_path: Path = BEAST_RALLY_STAMINA_LEDGER_FILE,
                           item_path: Path = BEAST_RALLY_ITEM_TRANSACTION_FILE,
                           config_dir: Path = CONFIG_DIR) -> bool:
    """Fail closed for persisted unresolved inputs, including previous days.

    Caller must own the account lease. Invalid storage raises instead of
    treating a malformed or unreadable journal as an empty one.
    """
    if not _valid_identity(identity):
        raise ValueError("complete stable MuMu identity required")
    if load_beast_stamina_item_pending(identity, path=item_path) is not None:
        return True
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    marker = config_dir / f"beast_single_shield_plus_pending_{digest}.marker"
    try:
        marker.stat()
    except FileNotFoundError:
        pass
    else:
        return True
    try:
        data = json.loads(stamina_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False
    if (not isinstance(data, dict) or data.get("version") not in (1, 2)
            or not isinstance(data.get("accounts"), dict)):
        raise ValueError("invalid stamina ledger; preserve and stop")
    entry = data["accounts"].get(identity)
    if entry is None:
        return False
    if not isinstance(entry, dict) or not isinstance(entry.get("day"), str):
        raise ValueError("invalid stamina account; preserve and stop")
    for field in ("reserved", "uncertain"):
        amount = entry.get(field, 0)
        if type(amount) is not int or amount < 0:
            raise ValueError("invalid stamina action; preserve and stop")
        # uncertain is a conservative budget debit after a reservation was
        # reconciled; unlike reserved it is not a pending input to replay.
        if field == "reserved" and amount:
            return True
    return False


class ManagedBeastSupervisor:
    """A single background coordinator for explicitly registered accounts.

    ``acquire(identity)`` returns an acquired lease or None. ``identify`` must
    read the actual selected device afresh. ``pending`` must inspect *all*
    durable action records.  The caller must ensure ``run`` uses
    ``perform_if_current`` for each input and records uncertain inputs before
    they are sent.  This coordinator never adopts old workers and never
    infers recoverability from a thread exit.
    """
    def __init__(self, acquire, identify, pending, run, report=lambda identity, msg: None, *, path=SUPERVISION_FILE, reconcile=None):
        self.acquire, self.identify, self.pending, self.run = acquire, identify, pending, run
        self.report, self.path = report, path
        # The optional callback only inspects frames and reconciles existing
        # receipts; it must never issue or replay a game input.
        self.reconcile = reconcile
        self._queue = queue.Queue()
        self._closing = threading.Event()
        self._active = set()
        self._registered = {}
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._loop, name="beast-supervisor", daemon=True)

    def start(self):
        self._thread.start()

    def close(self):
        self._closing.set()
        self._queue.put(None)
        self._thread.join(timeout=2)

    def register(self, identity, generation):
        if self._closing.is_set():
            raise RuntimeError("监督线程已停止")
        if not token_matches(read_intent(identity, path=self.path), generation):
            raise ValueError("必须由当前明确启动意图登记账号")
        with self._lock:
            self._registered[identity] = generation

    def recover(self, identity, generation, *, reason):
        """Queue only a caller-proven pre-input transport failure.

        An unknown or post-input failure is not recoverable here, even if a
        caller happens to observe an idle thread or an apparently idle UI.
        """
        if self._closing.is_set() or reason != "pre_input_transport":
            return False
        with self._lock:
            if self._registered.get(identity) != generation or identity in self._active:
                return False
            self._active.add(identity)
        self._queue.put((identity, generation))
        return True

    def _loop(self):
        while not self._closing.is_set():
            request = self._queue.get()
            if request is None:
                return
            identity, generation = request
            threading.Thread(target=self._run_one, args=(identity, generation), daemon=True,
                             name="beast-managed-account").start()

    def _run_one(self, identity, generation):
        lease = None
        try:
            if self._closing.is_set() or not token_matches(read_intent(identity, path=self.path), generation):
                return
            lease = self.acquire(identity)
            if lease is None:
                self.report(identity, "账号租约繁忙，未启动")
                return
            if self._closing.is_set() or self.identify(identity) != identity:
                self.report(identity, "账号实时身份不匹配，未启动")
                return
            if not token_matches(read_intent(identity, path=self.path), generation):
                return
            if self.pending(identity):
                if self.reconcile is not None:
                    self.reconcile(identity, generation)
                self.report(identity, "存在未决操作，保留并不启动")
                return
            self.run(identity, generation)
        except Exception as exc:
            self.report(identity, f"监督恢复停止：{type(exc).__name__}: {exc}")
        finally:
            if lease is not None:
                lease.release()
            with self._lock:
                self._active.discard(identity)
