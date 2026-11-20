from argparse import Namespace
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event
from time import monotonic
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from scripts import run_fortress_route as script
import wjdr_fortress as fortress
import wjdr_fortress_flow as flow
from wjdr_mumu_ipc import RouteCapture


EXAMPLE = Path(__file__).resolve().parents[1] / "scripts/fortress_route.example.json"


class FortressRouteScriptTests(unittest.TestCase):
    def test_scheduled_start_waits_until_due_and_rejects_stale_start(self):
        due = script.read_plan(EXAMPLE).round_start
        now = due - timedelta(seconds=3)
        stop = Mock()
        stop.is_set.return_value = False

        def wait(seconds):
            nonlocal now
            now += timedelta(seconds=seconds)

        stop.wait.side_effect = wait
        script.wait_for_start(due, stop, clock=lambda: now)
        stop.wait.assert_called_once_with(3)
        self.assertEqual(now, due)
        with self.assertRaisesRegex(ValueError, "预约已错过"):
            script.wait_for_start(due, stop, clock=lambda: due + timedelta(seconds=31))

    def test_scheduled_start_is_claimed_once_and_only_at_the_due_time(self):
        plan = script.read_plan(EXAMPLE)
        run = script.route_state(plan, None)
        save = Mock()
        with self.assertRaisesRegex(ValueError, "还未到点"):
            script.claim_scheduled_start(run, plan.round_start, save, now=plan.round_start - timedelta(seconds=1))
        save.assert_not_called()
        script.claim_scheduled_start(run, plan.round_start, save, now=plan.round_start)
        self.assertEqual(run["scheduled_start"], fortress.format_stamp(plan.round_start))
        with self.assertRaisesRegex(ValueError, "已提交"):
            script.claim_scheduled_start(run, plan.round_start, save, now=plan.round_start + timedelta(seconds=2))
        save.assert_called_once()
        with self.assertRaisesRegex(ValueError, "保留原路线"):
            script.route_state(replace(plan, stops=tuple(reversed(plan.stops))), run)

    def test_resolved_target_survives_resume_without_changing_route(self):
        plan = script.read_plan(EXAMPLE)
        stops = fortress.parse_route([("985", "唯一堡垒 单撞"), ("ZYT", "堡垒2 集结")])
        plan = replace(plan, stops=stops)
        run = script.route_state(plan, None)
        original = run["route"][0]
        save = Mock()
        with (patch.object(fortress, "open_fortress_activity") as open_activity,
              patch.object(fortress, "_wait_alliance_page", return_value=(None, 11))):
            resolved = flow.resolve_targets(Mock(), Mock(), Event(), run, original, save)
            self.assertEqual(resolved["targets"][0]["number"], 11)
            self.assertIsNone(original["targets"][0]["number"])
            resumed = script.route_state(plan, run)
            self.assertEqual(flow.resolve_targets(Mock(), Mock(), Event(), resumed, original, save), resolved)
        open_activity.assert_called_once()
        save.assert_called_once()

    @staticmethod
    def ipc_target():
        adb = Mock(device="127.0.0.1:16448", device_identities={})
        adb.players = [{"index": "2", "adb_port": 16448}]
        adb._run.return_value = "1234abcd\n8e5a12ad-9365-4809-8baf-f031fc00a381\nPhysical size: 1440x2560"
        return adb

    def test_preview_and_disabled_key_step_never_bind(self):
        with patch.object(script, "bind") as bind, patch("builtins.print"):
            self.assertEqual(script.main([str(EXAMPLE)]), 0)
            self.assertEqual(script.main([str(EXAMPLE), "--step", "return-keys", "--execute"]), 1)
            self.assertEqual(script.main([str(EXAMPLE), "--step", "key-record", "--execute"]), 1)
        bind.assert_not_called()

    def test_auto_reward_only_opens_mail_after_occupation_is_verified(self):
        plan = script.read_plan(EXAMPLE)
        run = script.route_state(plan, None)
        tag = run["route"][0]["alliance"]
        run["applications"][tag] = {"state": "joined", "started_at": plan.round_start.timestamp()}
        mail = fortress.RewardMail(plan.round_start + timedelta(seconds=1), "堡垒争夺胜利", False)
        args = Namespace(step="auto-reward")

        def collect(_target, _ocr, _stop, record, *, claim, verified, on_claimed):
            self.assertTrue(claim)
            self.assertEqual(verified[1], mail)
            self.assertIsNone(on_claimed)
            self.assertIn(tag, run["occupied"])
            record(mail, "pending")
            record(mail, "claimed")
            return mail

        with patch.object(script, "check_occupation", side_effect=ValueError("未占领")) as check, \
             patch.object(fortress, "open_recent_victory_mail", return_value=(Mock(), mail)) as open_mail, \
             patch.object(fortress, "collect_reward", side_effect=collect):
            with self.assertRaisesRegex(ValueError, "未占领"):
                script.run_step(args, Mock(), Mock(), Event(), run, Mock(), [])
            open_mail.assert_not_called()
            check.side_effect = None
            script.run_step(args, Mock(), Mock(), Event(), run, Mock(), [])
        self.assertEqual(run["mail"][tag][fortress.format_stamp(mail.stamp)], "claimed")

    def test_fast_clicks_keep_their_own_cadence_and_stop_on_page_change(self):
        stop = Event()
        ticks = []
        changed_at = []
        inspected = 0

        def inspect():
            nonlocal inspected
            inspected += 1
            stop.wait(0.15)
            if inspected >= 4:
                if not changed_at:
                    changed_at.append(monotonic())
                return False
            return True

        count = fortress.rapid_join_taps(lambda: ticks.append(monotonic()), inspect, stop, duration=1.5)
        self.assertEqual(count, len(ticks))
        self.assertGreaterEqual(count, 3)
        self.assertLess(ticks[-1], changed_at[0])
        self.assertTrue(all(right - left >= 0.09 for left, right in zip(ticks, ticks[1:])))

    def test_fast_clicks_pause_then_resume_after_a_short_button_change(self):
        stop = Event()
        ticks = []
        started = monotonic()

        def inspect():
            elapsed = monotonic() - started
            return not 0.24 <= elapsed < 0.46

        fortress.rapid_join_taps(lambda: ticks.append(monotonic() - started), inspect, stop, duration=0.79)
        self.assertTrue(any(tick < 0.24 for tick in ticks))
        self.assertFalse(any(0.28 <= tick < 0.46 for tick in ticks))
        self.assertTrue(any(tick >= 0.46 for tick in ticks))

    def test_rapid_timeout_reports_once_and_explicit_continue_can_use_unlimited_duration(self):
        plan = script.read_plan(EXAMPLE)
        run = script.route_state(plan, None)
        tag = run["route"][0]["alliance"]
        notify = Mock()
        stop = Event()

        def click_twice(tap, *_args, **_kwargs):
            tap()
            tap()
            return 2

        with patch.object(fortress, "rapid_join_anchor", return_value=((1, 2), Mock())), \
             patch.object(fortress, "confirm_direct_join", side_effect=ValueError("未入盟")), \
             patch.object(fortress, "rapid_join_taps", side_effect=click_twice) as clicks:
            result = fortress.run_rapid_join(Mock(), Mock(), stop, run, tag, Mock(), duration=0, on_timeout=notify)
            self.assertFalse(result.joined)
            self.assertEqual(run["applications"][tag]["state"], "timed_out")
            notify.assert_called_once()
            fortress.run_rapid_join(Mock(), Mock(), stop, run, tag, Mock(), duration=None, on_timeout=notify)
            self.assertIsNone(clicks.call_args.kwargs["duration"])
            notify.assert_called_once()

    def test_join_page_change_after_single_tap_routes_to_confirmation_before_repeating(self):
        stop = Event()
        target = Mock()
        run = {"applications": {}}
        with patch.object(fortress, "rapid_join_anchor", return_value=((1, 2), Mock(return_value=True))), \
             patch.object(fortress, "_join_page_still_ready", return_value=False), \
             patch.object(fortress, "confirm_direct_join") as confirm, \
             patch.object(fortress, "rapid_join_taps") as repeated:
            result = fortress.run_rapid_join(target, Mock(), stop, run, "RR3", Mock())
        self.assertTrue(result.joined)
        self.assertEqual(run["applications"]["RR3"]["state"], "joined")
        target.shell.assert_called_once_with(["cmd", "input", "tap", "1", "2"], timeout=0.8)
        confirm.assert_called_once()
        repeated.assert_not_called()

    def test_join_confirmation_waits_after_closing_relocation_prompt(self):
        target = Mock()
        stop = Event()
        frame = Mock()
        lines = [
            {"text": text, "words": [{"x": x, "y": y}]}
            for text, x, y in (("迁城", 309, 135), ("距离过远", 75, 864))
        ]

        def wait_for(_target, _ocr, _stop, identify, _error, **_kwargs):
            result = identify(Mock(), lines)
            if result is not None:
                return frame, result
            return frame, identify(Mock(), [])

        with patch.object(fortress, "_wait_alliance_page", side_effect=wait_for) as wait, \
             patch.object(fortress, "joined_tag_matches", side_effect=lambda _im, rows, *_args: not rows), \
             patch.object(fortress, "tap_game_point") as tap:
            fortress.confirm_direct_join(target, Mock(), stop, "AAA")
        self.assertEqual(wait.call_count, 2)
        tap.assert_called_once_with(target, frame, (622, 148))

    def test_auto_route_advances_in_order_after_verified_mail(self):
        plan = script.read_plan(EXAMPLE)
        run = script.route_state(plan, None)
        visited = []
        collected = []

        def visit(_target, _ocr, _stop, _run, tag, *_rest):
            visited.append(tag)

        def claim(_target, _ocr, _stop, state, tag, _save, **_kwargs):
            collected.append(tag)
            stamp = plan.round_start + timedelta(seconds=len(collected))
            state["mail"].setdefault(tag, {})[fortress.format_stamp(stamp)] = "claimed"
            return fortress.RewardMail(stamp, "堡垒争夺胜利", True)

        with patch.object(flow, "_visit", side_effect=visit), patch.object(flow, "_member_to_root"), \
             patch.object(flow, "_occupation", return_value=True), patch.object(flow, "claim_victory", side_effect=claim), \
             patch.object(flow, "_detail_back"), patch.object(fortress, "capture_reward", return_value=(None, None)):
            message = flow.run_route(Mock(), Mock(), Event(), run, Mock(), notify=Mock(), on_timeout=Mock())
        expected = [stop["alliance"] for stop in run["route"]]
        self.assertEqual(visited, expected)
        self.assertEqual(collected, [stop["alliance"] for stop in run["route"] for _ in stop["targets"]])
        self.assertEqual(run["index"], len(expected))
        self.assertIn("完成", message)

    def test_default_station_waits_for_all_resolved_victory_mails(self):
        plan = replace(script.read_plan(EXAMPLE), stops=fortress.parse_route([("BBK", "全部报名")]))
        run = script.route_state(plan, None)
        collected = []

        def claim(_target, _ocr, _stop, state, tag, _save, **_kwargs):
            self.assertEqual(state["index"], 0)
            stamp = plan.round_start + timedelta(seconds=len(collected) + 1)
            collected.append(stamp)
            state["mail"].setdefault(tag, {})[fortress.format_stamp(stamp)] = "claimed"
            return fortress.RewardMail(stamp, "堡垒争夺胜利", True)

        with (patch.object(flow, "_visit"), patch.object(flow, "_member_to_root"),
              patch.object(fortress, "open_fortress_activity"),
              patch.object(fortress, "_wait_alliance_page", return_value=(None, (("堡垒", 11), ("要塞", 1)))),
              patch.object(flow, "_occupation", return_value=True) as occupation,
              patch.object(flow, "claim_victory", side_effect=claim),
              patch.object(flow, "_detail_back") as back,
              patch.object(fortress, "capture_reward", return_value=(None, None))):
            flow.run_route(Mock(), Mock(), Event(), run, Mock(), notify=Mock(), on_timeout=Mock())
        verified = occupation.call_args.args[3]
        self.assertTrue(verified["all_registered"])
        self.assertEqual(len(verified["targets"]), 2)
        self.assertEqual(len(collected), 2)
        back.assert_called_once()
        self.assertEqual(run["index"], 1)

    def test_deferred_mail_returns_after_the_remaining_route(self):
        plan = replace(script.read_plan(EXAMPLE), stops=fortress.parse_route([
            ("QQQ", "堡垒9 单撞"), ("ZYT", "堡垒2 集结"), ("RMB", "堡垒7 集结"),
        ]))
        run = script.route_state(plan, None)
        run["index"] = 1
        run["deferred_victory"] = {"QQQ": plan.round_start.timestamp()}
        order = []

        def claim(_target, _ocr, _stop, state, tag, _save, **_kwargs):
            order.append(tag)
            stamp = plan.round_start + timedelta(seconds=len(order))
            state["mail"].setdefault(tag, {})[fortress.format_stamp(stamp)] = "claimed"
            return fortress.RewardMail(stamp, "堡垒争夺胜利", True)

        with (patch.object(flow, "_visit"), patch.object(flow, "_member_to_root"),
              patch.object(flow, "_occupation", return_value=True),
              patch.object(flow, "claim_victory", side_effect=claim),
              patch.object(fortress, "capture_reward", return_value=(None, None))):
            flow.run_route(Mock(), Mock(), Event(), run, Mock(), notify=Mock(), on_timeout=Mock())
        self.assertEqual(order, ["ZYT", "RMB", "QQQ"])
        self.assertEqual(run["deferred_victory"], {})
        self.assertEqual(run["index"], 3)

    def test_paired_mails_keep_the_earlier_reward_with_the_deferred_alliance(self):
        plan = replace(script.read_plan(EXAMPLE), stops=fortress.parse_route([
            ("QQQ", "堡垒9 单撞"), ("ZYT", "堡垒2 集结"),
        ]))
        run = script.route_state(plan, None)
        run["index"] = 1
        run["deferred_victory"] = {"QQQ": plan.round_start.timestamp()}
        times = [plan.round_start + timedelta(seconds=offset) for offset in (5, 9)]
        run["paired_victory"] = {"earlier": "QQQ", "later": "ZYT",
                                 "stamps": [fortress.format_stamp(stamp) for stamp in times]}
        order = []

        def claim(_target, _ocr, _stop, state, tag, _save, *, expected_stamp, **_kwargs):
            order.append((tag, expected_stamp))
            state["mail"].setdefault(tag, {})[fortress.format_stamp(expected_stamp)] = "claimed"
            return fortress.RewardMail(expected_stamp, "堡垒争夺胜利", True)

        with (patch.object(flow, "_visit"), patch.object(flow, "_member_to_root"),
              patch.object(flow, "_occupation", return_value=True),
              patch.object(flow, "claim_victory", side_effect=claim),
              patch.object(flow, "_detail_back") as back):
            flow.run_route(Mock(), Mock(), Event(), run, Mock(), notify=Mock(), on_timeout=Mock())
        self.assertEqual(order, list(zip(("QQQ", "ZYT"), times)))
        self.assertEqual(run["index"], 2)
        self.assertEqual(run["deferred_victory"], {})
        back.assert_called_once()

    def test_occupation_retries_read_failure_and_refreshes_both_directions(self):
        station = {"alliance": "985", "targets": [{"kind": "堡垒", "number": 10, "mode": "单撞"}]}
        target, ocr, frame, stop = Mock(), Mock(), Mock(), Mock()
        stop.is_set.return_value = False
        stop.wait.return_value = False

        def page(_target, _ocr, _stop, identify, _error):
            current = next(frames)
            if current is None:
                raise fortress.PageNotVerified("temporary OCR miss")
            return frame, identify(Mock(), current)

        frames = iter([None, "fortress", "adjacent", "occupied"])
        occupations = {"fortress": set(), "adjacent": None, "occupied": {("堡垒", 10)}}
        with (patch.object(fortress, "open_game_screen"),
              patch.object(fortress, "_wait_alliance_page", side_effect=page),
              patch.object(fortress, "read_occupation", side_effect=lambda _, lines, _ocr: occupations[lines]),
              patch.object(fortress, "is_regular_activity", return_value=True),
              patch.object(fortress, "fortress_tab_point", return_value=(586, 134)),
              patch.object(flow, "_refresh_tab_point", return_value=(400, 133)),
              patch.object(flow, "_tap") as tap):
            self.assertTrue(flow._occupation(target, ocr, stop, station, lambda: False))
        self.assertEqual([call.args[-1] for call in tap.call_args_list], [(400, 133), (586, 134)])

    def test_victory_mail_wait_refreshes_without_advancing_early(self):
        plan = replace(script.read_plan(EXAMPLE), stops=fortress.parse_route([("RMB", "堡垒7 集结")]))
        run = script.route_state(plan, None)
        stop = Mock()
        stop.is_set.return_value = False
        stop.wait.return_value = False
        attempt = 0

        def claim(_target, _ocr, _stop, state, tag, _save, **_kwargs):
            nonlocal attempt
            self.assertEqual(state["index"], 0)
            attempt += 1
            if attempt == 1:
                raise fortress.MailNotYetVisible("邮件尚未送达")
            if attempt == 2:
                raise fortress.PageNotVerified("页面还未加载完整")
            stamp = plan.round_start + timedelta(seconds=1)
            state["mail"].setdefault(tag, {})[fortress.format_stamp(stamp)] = "claimed"
            return fortress.RewardMail(stamp, "堡垒争夺胜利", True)

        with (patch.object(flow, "_visit"), patch.object(flow, "_member_to_root"),
              patch.object(flow, "_occupation", return_value=True),
              patch.object(flow, "claim_victory", side_effect=claim),
              patch.object(flow, "_refresh_alliance_mail") as refresh,
              patch.object(fortress, "capture_reward", return_value=(None, None))):
            flow.run_route(Mock(), Mock(), stop, run, Mock(), notify=Mock(), on_timeout=Mock())
        self.assertEqual(attempt, 3)
        refresh.assert_called_once()
        self.assertEqual(run["index"], 1)

    def test_cli_timeout_resume_continues_route_without_replaying_schedule(self):
        initial = ["plan.json", "--step", "auto-route", "--wait-start", "--execute"]
        retry = ["plan.json", "--step", "rapid-enter", "--rapid-alliance", "ABC", "--execute"]
        resume = ["plan.json", "--step", "auto-route", "--execute"]
        with patch.object(script, "_run_main", side_effect=[(retry, resume), 0, 0]) as runner:
            self.assertEqual(script.main(initial), 0)
        self.assertEqual([call.args[0] for call in runner.call_args_list], [initial, retry, resume])

    def test_key_flag_reuses_mail_records_and_only_enables_return_queue(self):
        plan = script.read_plan(EXAMPLE)
        run = script.route_state(plan, None)
        stamp = plan.round_start + timedelta(minutes=3)
        fortress.record_mail(run, "ZYZ", stamp, "claimed", stamp + timedelta(minutes=1))
        self.assertEqual(fortress.return_queue(run), [])
        enabled = script.route_state(replace(plan, take_keys=True), run)
        self.assertEqual(enabled["mail"], run["mail"])
        self.assertEqual(fortress.return_queue(enabled), [(stamp + timedelta(minutes=30), "ZYZ")])
        self.assertFalse(run["take_keys"])

    def test_return_keys_uses_the_earliest_verified_deadline(self):
        now = datetime.now(fortress.SHANGHAI)
        plan = replace(script.read_plan(EXAMPLE), round_start=now - timedelta(minutes=40), take_keys=True)
        run = script.route_state(plan, None)
        fortress.record_mail(run, "ZYZ", now - timedelta(minutes=10), "claimed", now)
        fortress.record_mail(run, "BBK", now - timedelta(minutes=20), "claimed", now)
        save = Mock()
        args = Namespace(step="return-keys", leave_current=True)
        with patch.object(fortress, "enter_route_alliance", return_value=fortress.AllianceVisit(True, "已进入")) as enter:
            script.run_step(args, Mock(), Mock(), Event(), run, save, [])
        self.assertEqual(enter.call_args.args[4], "BBK")
        self.assertEqual(enter.call_args.kwargs["return_by"], fortress.return_deadline(run, "BBK"))
        self.assertIn("BBK", run["returned"])
        save.assert_called_once()

    def test_ipc_failure_stops_without_adb_screenshot(self):
        adb = self.ipc_target()
        with patch("wjdr_mumu_ipc._IpcCapture", side_effect=ValueError("显示已改变")):
            with RouteCapture(adb, 2) as capture, self.assertRaisesRegex(RuntimeError, "IPC 抓帧失败"):
                capture.screenshot()
        adb.screenshot.assert_not_called()
        adb._run.assert_called_once()

    def test_capture_only_reads_from_ipc_and_closes_the_session(self):
        adb, ipc = self.ipc_target(), Mock()
        frame = Image.new("RGB", (1440, 2560), "blue")
        ipc.screenshot.return_value = frame
        with patch("wjdr_mumu_ipc._IpcCapture", return_value=ipc) as start:
            with RouteCapture(adb, 2) as capture:
                self.assertIs(capture.screenshot(), frame)
                self.assertIs(capture.screenshot(), frame)
        self.assertEqual(start.call_args.args, (adb, 2, (1440, 2560)))
        self.assertTrue(start.call_args.kwargs["game_display"])
        ipc.close.assert_called_once()
        adb.screenshot.assert_not_called()
