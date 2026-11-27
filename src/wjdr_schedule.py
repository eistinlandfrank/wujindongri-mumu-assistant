"""Persisted one-shot schedules. Claim before callback: never replay a start."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from wjdr_backend import CONFIG_DIR, _atomic_json_write, _serialized_account_write

SCHEDULE_FILE = CONFIG_DIR / "scheduled_starts.json"
GRACE_SECONDS = 30
STATES = {"pending": "等待时间", "claimed": "正在核验手机", "running": "已启动",
          "finished": "流程已结束", "cancelled": "已取消", "missed": "已错过",
          "skipped": "未执行", "failed": "启动失败"}
TASK_NAMES = {"beast_rally": "巨兽集结", "fortress_route": "堡垒跑联盟", "bear": "打熊 · 每两天"}
BEAR_REPEAT_SECONDS = 2 * 24 * 60 * 60


def read_jobs(path: Path = SCHEDULE_FILE) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("定时任务文件格式异常，已停止自动触发；请检查记录")
    return payload["jobs"]


def _write(path, jobs):
    _atomic_json_write(path, {"version": 1, "jobs": jobs})


@_serialized_account_write
def add_job(identity: str, device: str, label: str, run_at: float, *,
            task: str = "beast_rally", route: list[dict] | None = None,
            fortress_take_keys: bool | None = None,
            bear: dict | None = None,
            now: float | None = None, path: Path = SCHEDULE_FILE) -> dict:
    now = time.time() if now is None else now
    if not identity.startswith("mumu:") or ":android:" not in identity:
        raise ValueError("请先连接并确认手机身份，再保存定时任务")
    if run_at <= now:
        raise ValueError("请选择未来的日期和时间")
    if task not in TASK_NAMES or (task == "fortress_route" and not route):
        raise ValueError("请确认预约任务及路线")
    if fortress_take_keys is not None and (task != "fortress_route" or type(fortress_take_keys) is not bool):
        raise ValueError("仅堡垒路线预约可保存拿钥匙选项")
    jobs = read_jobs(path)
    if task == "bear":
        from datetime import datetime, time as clock_time
        from wjdr_bear import ZONE, roster_settings
        if not isinstance(bear, dict) or datetime.fromtimestamp(run_at, ZONE).time() != clock_time(20, 30):
            raise ValueError("请选择首场打熊日期，固定北京时间 20:30 开始")
        bear = roster_settings(bear.get("names"), bear.get("player"))
        if any(j["identity"] == identity and j.get("task") == "bear" and j["state"] == "pending" for j in jobs):
            raise ValueError("该手机已有打熊预约，可在「定时启动」取消后重新设置")
    if any(j["identity"] == identity and j["state"] in {"pending", "claimed"}
           and abs(j["run_at"] - run_at) < GRACE_SECONDS for j in jobs):
        raise ValueError("该手机在此时间附近已有预约，请勿重复添加")
    if len(jobs) >= 200:
        raise ValueError("最多保存200条记录，请先清除已结束记录")
    job = dict(id=os.urandom(16).hex(), identity=identity, device=device, label=label,
               task=task, run_at=float(run_at), created_at=now,
               state="pending", note="到点核验手机后启动一次；不会唤醒电脑")
    if task == "fortress_route":
        job["route"] = route
        if fortress_take_keys is not None:
            job["fortress_take_keys"] = fortress_take_keys
    if task == "bear":
        job.update(bear=bear, series=job["id"], note="北京时间 20:30，隔两天启动；不会唤醒电脑")
    jobs.append(job)
    _write(path, jobs)
    return dict(job)


@_serialized_account_write
def claim_due(identity: str, *, busy: bool = False, now: float | None = None,
              path: Path = SCHEDULE_FILE) -> dict | None:
    now = time.time() if now is None else now
    jobs = read_jobs(path)
    changed = False
    chosen = None
    for job in sorted(jobs, key=lambda j: j["run_at"]):
        if job.get("task") == "bear" and job["state"] == "pending" and job["run_at"] <= now:
            elapsed = int((now - job["run_at"]) // BEAR_REPEAT_SECONDS)
            current_at = job["run_at"] + elapsed * BEAR_REPEAT_SECONDS
            if job["identity"] != identity and now <= current_at + GRACE_SECONDS:
                continue
            next_at = current_at + BEAR_REPEAT_SECONDS
            # The current occurrence and its successor are committed together.
            # Preserve the original two-day cadence across shutdowns.
            job["run_at"] = current_at
            history = [entry for entry in jobs if entry.get("series") == job["series"]
                       and entry["state"] not in {"pending", "claimed", "running"}]
            for old in sorted(history, key=lambda row: row["run_at"])[:-5]:
                jobs.remove(old)
            future = {key: job[key] for key in ("identity", "device", "label", "task", "bear", "series")}
            future.update(id=os.urandom(16).hex(), run_at=next_at, created_at=now, state="pending",
                          note="北京时间 20:30，隔两天启动；不会唤醒电脑")
            jobs.append(future)
            changed = True
        if job["state"] == "pending" and now > job["run_at"] + GRACE_SECONDS:
            job.update(state="missed", note="超过预约时间30秒；不补跑，请重新预约")
            changed = True
        elif job["state"] == "claimed" and now > job["claimed_at"] + GRACE_SECONDS:
            job.update(state="failed", note="启动核验超时或助手退出；未自动重试，请检查运行日志")
            changed = True
        if (chosen is None and job["identity"] == identity and
                job["state"] == "pending" and job["run_at"] <= now):
            if busy:
                job.update(state="skipped", note="本窗口已有任务运行；未打断当前任务")
            else:
                job.update(state="claimed", token=os.urandom(16).hex(), claimed_at=now,
                           owner_pid=os.getpid(), note="已锁定本次启动，正在核验设备身份")
                chosen = dict(job)
            changed = True
    if changed:
        _write(path, jobs)
    return chosen


@_serialized_account_write
def transition(job_id: str, token: str, state: str, note: str, *,
               path: Path = SCHEDULE_FILE) -> bool:
    jobs = read_jobs(path)
    for job in jobs:
        allowed = ({"running", "failed", "skipped"} if job["state"] == "claimed"
                   else {"finished", "failed"} if job["state"] == "running" else set())
        if job["id"] == job_id and job.get("token") == token and state in allowed:
            job.update(state=state, note=note, updated_at=time.time())
            _write(path, jobs)
            return True
    return False


@_serialized_account_write
def cancel_job(job_id: str, *, path: Path = SCHEDULE_FILE) -> bool:
    jobs = read_jobs(path)
    for job in jobs:
        if job["id"] == job_id and job["state"] in {"pending", "claimed"}:
            job.update(state="cancelled", note="用户取消预约；不会启动")
            _write(path, jobs)
            return True
    return False


@_serialized_account_write
def clear_history(*, path: Path = SCHEDULE_FILE) -> None:
    _write(path, [j for j in read_jobs(path) if j["state"] in {"pending", "claimed", "running"}])


@_serialized_account_write
def cancel_waiting(identity: str | None = None, *, claimed_only: bool = False,
                   path: Path = SCHEDULE_FILE) -> None:
    jobs = read_jobs(path)
    changed = False
    for job in jobs:
        if ((identity is None or job["identity"] == identity) and
                job["state"] in ({"claimed"} if claimed_only else {"pending", "claimed"})):
            job.update(state="cancelled", note="用户停止启动 / 全局急停，预约已取消")
            changed = True
    if changed:
        _write(path, jobs)
