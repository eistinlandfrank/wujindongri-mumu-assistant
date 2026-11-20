from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image

import wjdr_fortress as fortress


def line(x, y, text):
    return {"text": text, "words": [{"x": x, "y": y}]}


class FortressTests(unittest.TestCase):
    def setUp(self):
        route = fortress.parse_route([
            ("BBK", "堡垒11 集结"), ("520", "要塞4 集结，堡垒8 集结"),
        ])
        self.run_state = fortress.new_run(route, fortress.parse_stamp("2026-11-20 10:00:00"))

    def test_alliances_keep_separate_earliest_header_times(self):
        now = fortress.parse_stamp("2026-11-20 10:45:00")
        for alliance, text in [
            ("BBK", "2026-11-20 10:20:02"),
            ("BBK", "2026 一 11 一 20 10 ： 08 ： 31"),
            ("520", "2026-11-20 10:19:00"),
        ]:
            fortress.record_mail(self.run_state, alliance, fortress.parse_stamp(text), "claimed", now)
        queue = fortress.return_queue(self.run_state)
        self.assertEqual([(fortress.format_stamp(due), tag) for due, tag in queue],
                         [("2026-11-20 10:38:31", "BBK"), ("2026-11-20 10:49:00", "520")])
        self.run_state["keys"]["BBK"] = fortress.format_stamp(now)
        self.assertEqual(fortress.return_queue(self.run_state), queue[1:])

    def test_key_collection_status_does_not_confuse_return_with_claim(self):
        run = self.run_state
        tag = "520"
        sent = fortress.parse_stamp("2026-11-20 10:02:03")
        due = sent + timedelta(minutes=30)
        self.assertEqual(fortress.key_collection_status(run, tag, sent), "待登记胜利邮件")
        fortress.record_mail(run, tag, sent, "claimed", sent)
        self.assertEqual(fortress.key_collection_status(run, tag, sent), "待返回")
        self.assertEqual(fortress.key_collection_status(run, tag, due), "已过返回截止 · 无领取记录")
        run["returned"][tag] = fortress.format_stamp(due)
        self.assertEqual(fortress.key_collection_status(run, tag, due), "超时返回 · 无领取记录")
        run["returned"][tag] = fortress.format_stamp(due - timedelta(seconds=1))
        self.assertEqual(fortress.key_collection_status(run, tag, due), "已返回 · 领取待核对")
        receipt = {"stamp": fortress.format_stamp(due), "state": "pending"}
        run["key_mail"] = {tag: {"堡垒8": receipt}}
        self.assertEqual(fortress.key_collection_status(run, tag, due), "领取待核对")
        receipt["state"] = "claimed"
        self.assertEqual(fortress.key_collection_status(run, tag, due), "部分领取（1 封）")
        run["keys"][tag] = fortress.format_stamp(due)
        self.assertEqual(fortress.key_collection_status(run, tag, due), "已领取")

    def test_old_future_and_cross_alliance_mail_cannot_be_registered(self):
        now = fortress.parse_stamp("2026-11-20 10:45:00")
        for time in ["2026-11-20 09:59:59", "2026-12-20 10:20:02"]:
            with self.subTest(time=time), self.assertRaises(ValueError):
                fortress.record_mail(self.run_state, "BBK", fortress.parse_stamp(time), "claimed", now)
        fortress.record_mail(self.run_state, "BBK", now, "claimed", now)
        with self.assertRaises(ValueError):
            fortress.record_mail(self.run_state, "520", now, "claimed", now)

    def test_header_time_is_required_and_button_color_agrees(self):
        lines = [
            line(10, 10, "邮件"), line(259, 263, "堡 垒 争 夺 胜 利"),
            line(396, 124, "2026 一 11 一 20 10 ： 20 ： 02"),
            line(306, 750, "领 取"), line(166, 856, "将在2026-12-20 10:20:02失效"),
        ]
        green = Image.new("RGB", fortress.REFERENCE, (40, 180, 66))
        result = fortress.read_mail(green, lines)
        self.assertEqual(fortress.format_stamp(result.stamp), "2026-11-20 10:20:02")
        self.assertFalse(result.claimed)
        self.assertIsNone(fortress.read_mail(green, [*lines[:2], *lines[3:]]))
        self.assertIsNone(fortress.read_mail(green, [*lines[:3], line(306, 750, "已领取")]))
        self.assertIsNone(fortress.read_mail(green, [lines[0], line(259, 263, "联盟公告"), *lines[2:]]))

    def test_header_crop_reads_seconds_missed_by_full_page_ocr(self):
        lines = [
            line(10, 10, "邮件"), line(259, 263, "堡垒争夺胜利"), line(307, 749, "领取"),
            line(397, 124, "2026 一 11 一 20 10 ： 33 ： 2 如"),
            line(165, 856, "将在2026-12-20 10:33:24失效"),
        ]
        image = Image.new("RGB", fortress.REFERENCE, (40, 180, 66))
        ocr = Mock(return_value=[line(0, 0, "2026 一 11 一 20 10 ： 33 ： 24")])
        self.assertIsNone(fortress.read_mail(image, lines))
        result = fortress.read_mail(image, lines, ocr)
        self.assertEqual(fortress.format_stamp(result.stamp), "2026-11-20 10:33:24")
        self.assertEqual(ocr.call_args.args[0].size, (759, 114))
        contradictory = [*lines[:3], line(397, 124, "2026-11-20 10:33:21"), lines[-1]]
        self.assertIsNone(fortress.read_mail(image, contradictory, ocr))

    def test_header_crop_preserves_separated_clock_fields_without_colons(self):
        expected = fortress.parse_stamp("2026-11-20 12:11:47")
        self.assertEqual(fortress.parse_cropped_mail_stamp("2026 一 11 一 20 12 11 47"), expected)
        for text in ("2026-11-20 121147", "2026-11-20 12 1 47", "2026-11-20 12 11 47 00"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                fortress.parse_cropped_mail_stamp(text)

    def test_control_mail_requires_target_sent_time_and_matching_claim_button(self):
        lines = [line(10, 10, "邮件"), line(404, 124, "2026-11-20 13:10:36"),
                 line(259, 263, "成功控制堡垒"), line(45, 329, "恭喜，您的联盟顺利控制了3号要塞！"),
                 line(307, 588, "领取")]
        image = Image.new("RGB", fortress.REFERENCE, (40, 180, 66))
        reward = fortress.read_control_reward(image, lines)
        self.assertEqual((reward.target, reward.stamp, reward.point, reward.claimed),
                         ("要塞3", fortress.parse_stamp("2026-11-20 13:10:36"), (336, 602), False))
        self.assertIsNone(fortress.read_control_reward(image, [lines[0], *lines[2:]]))
        self.assertIsNone(fortress.read_control_reward(image, [*lines[:4], line(307, 588, "已领取")]))

    def test_normalized_viewport_keeps_noise_and_removes_letterbox(self):
        content = Image.new("RGB", fortress.REFERENCE, (173, 190, 204))
        letterbox = Image.new("RGB", (693, 1216), (0, 0, 0))
        letterbox.paste(content, (10, 10))
        self.assertEqual(fortress.normalize_frame(letterbox).tobytes(), content.tobytes())
        noise = content.copy()
        noise.paste((0, 0, 0), (0, 0, 673, 3))
        self.assertEqual(fortress.normalize_frame(noise).tobytes(), noise.tobytes())

    def test_blue_cards_must_match_the_configured_number_and_type(self):
        first, second = self.run_state["route"]
        self.assertTrue(fortress.occupation_complete({("堡垒", 11)}, first))
        self.assertFalse(fortress.occupation_complete({("要塞", 11), ("堡垒", 12)}, first))
        self.assertFalse(fortress.occupation_complete({("要塞", 4)}, second))
        self.assertFalse(fortress.occupation_complete({("堡垒", 4), ("堡垒", 8)}, second))
        self.assertTrue(fortress.occupation_complete({("要塞", 4), ("堡垒", 8)}, second))
        with self.assertRaises(ValueError):
            fortress.parse_targets("堡垒11 集结，堡垒11 单撞")

    def test_target_picker_accepts_mixed_targets_and_all_registered_defaults(self):
        picked = fortress.parse_targets("堡垒12 单撞、要塞4 集结、堡垒1 集结")
        self.assertEqual([(item.kind, item.number) for item in picked], [("堡垒", 12), ("要塞", 4), ("堡垒", 1)])
        self.assertEqual(fortress.parse_targets("默认"), (fortress.Target("全部报名", None, "按安排"),))
        for invalid in ("堡垒13 单撞", "要塞5 集结", "全部报名、要塞4 集结"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                fortress.parse_targets(invalid)

    def test_card_art_distinguishes_fortress_and_stronghold(self):
        image = Image.new("RGB", fortress.REFERENCE, "white")
        expected = ("要塞", "堡垒")
        for location, kind in zip((36, 226), expected):
            image.paste(Image.fromarray(fortress._target_art()[kind]), (location + 34, 868))
            self.assertEqual(fortress._target_kind(image, location), kind)
        self.assertIsNone(fortress._target_kind(image, 416))

    def test_unique_fortress_accepts_one_fortress_even_with_a_stronghold(self):
        image = Image.new("RGB", fortress.REFERENCE, "black")
        ocr = Mock(return_value=[line(0, 0, "11")])

        def put_card(left, kind):
            image.paste(Image.fromarray(fortress._target_art()[kind]), (left + 34, 868))
            image.paste("white", (left + 8, 839, left + 11, 853))

        with patch.object(fortress, "is_fortress_activity", return_value=True):
            put_card(226, "要塞")
            self.assertIsNone(fortress.read_unique_fortress(image, [], ocr))
            put_card(36, "堡垒")
            self.assertEqual(fortress.read_unique_fortress(image, [], ocr), 11)
            put_card(416, "堡垒")
            self.assertIsNone(fortress.read_unique_fortress(image, [], ocr))

    def test_all_registered_requires_complete_cards_and_every_target_blue(self):
        board = Image.new("RGB", fortress.REFERENCE, "black")
        for left, kind in ((36, "堡垒"), (226, "要塞")):
            board.paste(Image.fromarray(fortress._target_art()[kind]), (left + 34, 868))
            board.paste("white", (left + 8, 839, left + 11, 853))
        lines = [line(89, 25, "常规活动"), line(560, 1144, "堡垒争夺")]
        ocr = Mock(return_value=[])
        with patch.object(fortress, "_target_number", return_value=1):
            for count in ("已报名1/3", "已报名3/3", "已报名0/3", "已报名3/2"):
                self.assertIsNone(fortress.read_registered_targets(board, [*lines, line(280, 790, count)], ocr))
            complete = [*lines, line(280, 790, "已 報 名 2 ／ 2")]
            self.assertEqual(fortress.read_registered_targets(board, complete, ocr), (("堡垒", 1), ("要塞", 1)))
            route = fortress.parse_route([("BBK", "全部报名")])
            run = fortress.new_run(route, fortress.parse_stamp("2026-11-20 12:00:00"))
            raw = run["route"][0]
            run["resolved_targets"] = {"BBK": [["堡垒", 1], ["要塞", 1]]}
            stop = fortress.resolved_station(run, raw)
            self.assertTrue(fortress.registration_matches(board, complete, ocr, stop))
            self.assertFalse(fortress.occupation_complete({("堡垒", 1)}, stop))
            self.assertFalse(fortress.occupation_complete({("堡垒", 1), ("要塞", 2)}, stop))
            self.assertTrue(fortress.occupation_complete({("堡垒", 1), ("要塞", 1)}, stop))

    def test_occupation_uses_blue_color_without_reading_the_label(self):
        image = Image.new("RGB", fortress.REFERENCE, (48, 75, 109))
        image.paste(Image.fromarray(fortress._target_art()["堡垒"]), (70, 868))
        image.paste("white", (44, 839, 47, 853))
        lines = [line(89, 25, "常规活动"), line(560, 1144, "堡垒争夺")]
        ocr = Mock()
        with patch.object(fortress, "_target_number", return_value=10):
            image.paste("white", (48, 985, 80, 995))
            self.assertEqual(fortress.read_occupation(image, lines, ocr), set())
            image.paste((22, 135, 218), (56, 979, 57, 1037))
            self.assertEqual(fortress.read_occupation(image, lines, ocr), set())
            image.paste((22, 135, 218), (48, 985, 80, 995))
            self.assertEqual(fortress.read_occupation(image, lines, ocr), {("堡垒", 10)})
        ocr.assert_not_called()

    def test_visible_mail_scan_excludes_announcements_and_old_rounds(self):
        lines = [
            line(10, 10, "邮件"), line(60, 102, "战争"), line(312, 103, "系统"),
            line(439, 102, "报告"), line(569, 102, "收藏"),
            line(165, 182, "堡垒争夺胜利"), line(165, 248, "2026 一 11 一 20 10 ： 20 ： 02"),
            line(165, 319, "联盟公告"), line(165, 383, "2026 一 11 一 20 10 ： 09 ： 36"),
            line(165, 723, "堡垒争夺胜利"), line(165, 790, "2026 一 11 一 20 10 ： 08 ： 31"),
            line(165, 860, "堡垒争夺胜利"), line(165, 927, "2026 一 11 一 19 10 ： 09 ： 36"),
        ]
        self.assertTrue(fortress.is_mail_list(lines))
        result = fortress.visible_reward_stamps(
            lines, fortress.parse_stamp("2026-11-20 10:00:00"), fortress.parse_stamp("2026-11-20 10:30:00"))
        self.assertEqual([fortress.format_stamp(stamp) for stamp in result],
                         ["2026-11-20 10:08:31", "2026-11-20 10:20:02"])

    def test_mail_list_crops_a_timestamp_with_a_missing_digit(self):
        lines = [line(165, 318, "堡垒争夺胜利"), line(165, 384, "2026一11一20153:10")]
        image = Image.new("RGB", fortress.REFERENCE)
        ocr = Mock(return_value=[line(0, 0, "2026一11一2015:43:10")])
        now = fortress.parse_stamp("2026-11-20 15:44:00")
        start = fortress.parse_stamp("2026-11-20 15:00:00")
        self.assertEqual(fortress.visible_reward_stamps(lines, start, now, image=image, ocr=ocr),
                         [fortress.parse_stamp("2026-11-20 15:43:10")])

    def test_overview_requires_tag_and_info_and_does_not_match_management(self):
        overview = [
            line(89, 21, "联 盟"), line(262, 101, "[ 520 ] 示例"),
            line(262, 157, "0 盟 主 ："), line(266, 190, "0 实 力 ："),
            line(302, 223, "排 名 ："),
        ]
        self.assertEqual(fortress.read_alliance(overview), "520")
        self.assertIsNone(fortress.read_alliance(overview[:2]))
        management = [line(89, 21, "管理"), line(463, 150, "联盟列表"), line(463, 388, "退出联盟")]
        self.assertTrue(fortress.is_alliance_settings(management))
        self.assertIsNone(fortress.read_alliance(management))

    def test_alliance_search_checks_exact_result_membership_and_access(self):
        lines = [
            line(10, 10, "令 联 盟 列 表"), line(53, 121, "BBK"),
            line(247, 214, "[ BBK ] 示例"), line(218, 286, "43 / 100"),
            line(505, 299, "需 要 申 请"),
        ]
        self.assertEqual(fortress.read_alliance_listing(lines, "BBK"),
                         fortress.AllianceListing(43, 100, "需要申请"))
        self.assertIsNone(fortress.read_alliance_listing(lines, "520"))
        self.assertIsNone(fortress.read_alliance_listing(
            [*lines[:2], line(247, 214, "[BBK2] 示例"), *lines[3:]], "BBK"))
        self.assertIsNone(fortress.read_alliance_listing(
            [*lines[:2], line(247, 214, "[bbk] 示例"), *lines[3:]], "BBK"))
        self.assertIsNone(fortress.read_alliance_listing(
            [*lines[:4], line(505, 512, "可直接加入")], "BBK"))

    def test_search_fallback_confirms_the_second_row_and_preserves_tag_case(self):
        lines = [
            line(89, 21, "联盟"), line(76, 110, "建立联盟"), line(498, 110, "邀请/申请"),
            line(57, 198, "QQQ"), line(190, 284, "[qqq]示例"),
            line(190, 489, "[QQ误示例"), line(528, 344, "申请"), line(528, 547, "申请"),
        ]
        image = Image.new("RGB", fortress.REFERENCE)
        ocr = Mock(return_value=[line(0, 0, "2/100")])
        with patch.object(fortress, "_cropped_listing_tag", side_effect=["qqq", "QQQ"]):
            self.assertEqual(fortress._listing_in_frame(image, lines, ocr, "QQQ"),
                             (489, fortress.AllianceListing(2, 100, "需要申请")))
        ocr.assert_called_once()

    def test_application_requires_exact_tag_and_distinguishes_gray_button(self):
        lines = [line(280, 170, "联盟资讯"), line(229, 241, "[BBK] 示例"), line(310, 929, "申 请")]
        gray = Image.new("RGB", fortress.REFERENCE, (102, 110, 120))
        green = Image.new("RGB", fortress.REFERENCE, (40, 180, 66))
        self.assertEqual(fortress.read_alliance_application(gray, lines, Mock()),
                         fortress.AllianceApplication("BBK", "gray"))
        self.assertEqual(fortress.read_alliance_application(green, lines, Mock()),
                         fortress.AllianceApplication("BBK", "ready"))
        self.assertEqual(fortress.read_alliance_application(gray, [*lines[:2], line(310, 929, "已申请")], Mock()),
                         fortress.AllianceApplication("BBK", "pending"))
        target = Mock()
        with patch.object(fortress, "_alliance_frame", return_value=(green, green, lines)):
            with self.assertRaisesRegex(ValueError, "当前联盟资讯为"):
                fortress.open_alliance_application(target, Mock(), Event(), "520")
        target.shell.assert_not_called()

    def test_already_gray_application_starts_wait_without_clicking_again(self):
        target = Mock()
        remember = Mock()
        frame = Image.new("RGB", fortress.REFERENCE, (102, 110, 120))
        with patch.object(fortress, "open_alliance_application",
                          return_value=(frame, fortress.AllianceApplication("BBK", "gray"))):
            fortress.start_alliance_application(target, Mock(), Event(), "BBK", remember)
        remember.assert_called_once_with(True)
        target.shell.assert_not_called()

    def test_application_persists_intent_before_sending_and_skips_existing_pending(self):
        target = Mock()
        frame = Image.new("RGB", fortress.REFERENCE, (40, 180, 66))
        remember = Mock()
        target.shell.side_effect = lambda *args, **kwargs: remember.assert_called_once_with(False)
        with (patch.object(fortress, "open_alliance_application",
                           return_value=(frame, fortress.AllianceApplication("BBK", "ready"))),
              patch.object(fortress, "_wait_alliance_page", return_value=(frame, "pending"))):
            fortress.start_alliance_application(target, Mock(), Event(), "BBK", remember)
        target.shell.assert_called_once_with(["input", "tap", "336", "943"], timeout=5)
        remember.reset_mock()
        target.shell.reset_mock()
        with patch.object(fortress, "open_alliance_application",
                          return_value=(frame, fortress.AllianceApplication("BBK", "pending"))):
            fortress.start_alliance_application(target, Mock(), Event(), "BBK", remember)
        remember.assert_called_once_with(True)
        target.shell.assert_not_called()

    def test_application_confirms_only_the_verified_inactive_leader_prompt(self):
        target, remember = Mock(), Mock()
        frame = Image.new("RGB", fortress.REFERENCE)
        with (patch.object(fortress, "open_alliance_application",
                           return_value=(frame, fortress.AllianceApplication("QQQ", "ready"))),
              patch.object(fortress, "_wait_alliance_page", return_value=(frame, "confirm")),
              patch.object(fortress, "tap_game_point") as tap):
            fortress.start_alliance_application(target, Mock(), Event(), "QQQ", remember)
        remember.assert_called_once_with(False)
        self.assertEqual([call.args[-1] for call in tap.call_args_list], [(336, 943), (451, 725)])

    def test_application_polling_uses_full_three_minutes_and_exits_on_join(self):
        now = 0
        stop = Mock()
        stop.is_set.return_value = False
        attempts = []

        def wait(seconds):
            nonlocal now
            now += seconds
        stop.wait.side_effect = wait

        def probe():
            attempts.append(now)
            return False

        self.assertFalse(fortress.wait_for_alliance(180, stop, probe, clock=lambda: now))
        self.assertEqual(attempts, list(range(0, 181, 10)))
        now = 0
        self.assertTrue(fortress.wait_for_alliance(180, stop, lambda: now >= 30, clock=lambda: now))
        self.assertEqual(now, 30)
        stop.is_set.return_value = True
        skipped = Mock()
        with self.assertRaises(InterruptedError):
            fortress.wait_for_alliance(180, stop, skipped, clock=lambda: now)
        skipped.assert_not_called()

    def test_own_member_controls_are_required_to_report_admission(self):
        overview = [
            line(89, 21, "联盟"), line(262, 101, "[BBK] 示例"), line(262, 157, "盟主："),
            line(266, 190, "实力："), line(302, 223, "排名："),
        ]
        self.assertIsNone(fortress.read_joined_alliance(overview))
        controls = [line(160, 1157, "成员"), line(314, 1157, "激励")]
        self.assertEqual(fortress.read_joined_alliance([*overview, *controls]), "BBK")

    def test_rapid_join_checks_short_tag_even_when_the_alliance_name_changes(self):
        heading = line(90, 20, "联盟")
        controls = [line(158, 1157, "成员"), line(470, 1157, "设置")]
        image = Image.new("RGB", fortress.REFERENCE)
        ocr = Mock(return_value=[line(0, 0, "[ABC")])
        for title in ("BC ] 示例甲", "BC ] 改名后的示例乙"):
            with self.subTest(title=title):
                lines = [heading, line(285, 103, title), *controls]
                self.assertTrue(fortress.joined_tag_matches(image, lines, ocr, "ABC"))
        self.assertFalse(fortress.joined_tag_matches(image, lines[:2], ocr, "ABC"))
        ocr.return_value = [line(0, 0, "[ABCI")]
        self.assertFalse(fortress.joined_tag_matches(image, lines, ocr, "ABC"))
        lines = [heading, line(285, 103, "R3 ] 示例"), *controls]
        larger_crop = Mock(side_effect=[[], [line(0, 0, "[RR3]")]])
        self.assertTrue(fortress.joined_tag_matches(image, lines, larger_crop, "RR3"))

    def test_alliance_exit_follows_the_exact_label_in_both_management_layouts(self):
        menu = [line(90, 21, "管理"), line(463, 149, "联盟列表")]
        original = line(463, 388, "退出联盟")
        successor = line(463, 388, "取代盟主")
        shifted = line(156, 507, "退出联盟")
        self.assertEqual(fortress.alliance_exit_point([*menu, original]), (510, 402))
        self.assertEqual(fortress.alliance_exit_point([*menu, successor, shifted]), (179, 520))
        relocated_list = line(156, 268, "朕盟列表")
        self.assertEqual(fortress.alliance_exit_point([menu[0], relocated_list, shifted]), (179, 520))
        expanded = [menu[0], line(156, 506, "联盟列表"), line(156, 744, "退出联盟")]
        self.assertEqual(fortress.alliance_exit_point(expanded), (179, 757))
        self.assertIsNone(fortress.alliance_exit_point([menu[0], shifted]))
        self.assertIsNone(fortress.alliance_exit_point([*menu, successor]))
        self.assertIsNone(fortress.alliance_exit_point([*menu, original, shifted]))

    def test_resume_from_management_confirms_membership_before_exit(self):
        menu = [line(90, 21, "管理"), line(463, 149, "联盟列表"), line(463, 388, "退出联盟")]
        member = [line(115, 29, "联盟")]
        target, ocr, frame = Mock(), Mock(), Mock()
        stop = Mock()
        stop.is_set.return_value = False
        frames = [(frame, None, menu)] * 2 + [(frame, None, member)] * 2

        def current(_image, lines, reader):
            self.assertIs(reader, ocr)
            return "BBK" if lines == member else None

        with (patch.object(fortress, "_alliance_frame", side_effect=frames),
              patch.object(fortress, "read_joined_in_frame", side_effect=current),
              patch.object(fortress, "tap_game_point") as tap):
            self.assertTrue(fortress.prepare_alliance_route(target, ocr, stop, "BBK", leave_current=True))
        tap.assert_called_once_with(target, frame, (37, 36))

    def test_alliance_transition_waits_for_two_matches_after_six_unsettled_frames(self):
        frames = [(None, None, [])] * 6 + [(None, None, ["new"])] * 2
        stop = Mock()
        stop.is_set.return_value = False
        with patch.object(fortress, "_alliance_frame", side_effect=frames) as read:
            _, label = fortress._wait_alliance_page(None, None, stop, lambda _image, lines: lines, "unsettled")
        self.assertEqual(label, ["new"])
        self.assertEqual(read.call_count, 8)

    def test_timeout_notifies_once_and_keeps_the_original_application(self):
        from wjdr_fortress_ui import FortressUI

        worker, signals, target, save = Mock(), Mock(), Mock(), Mock()
        ui = SimpleNamespace(_fortress_worker=worker, signals=signals, stop_event=Event(),
                             _fortress_current_stop=lambda run: run["route"][run["index"]])
        FortressUI._fortress_apply(ui)
        operation = worker.call_args.args[0]
        target.device = "test-2"
        target.device_identity.return_value = "mumu:2:android:test"

        def start(target, ocr, stop, tag, remember):
            remember(True)

        with patch.object(fortress, "start_alliance_application", side_effect=start) as submit, \
             patch.object(fortress, "prepare_alliance_route", return_value=False), \
             patch.object(fortress, "observe_alliance_application", return_value=None), \
             patch.object(fortress, "wait_for_alliance", return_value=False):
            first = operation(target, self.run_state, Mock(), save)
            second = operation(target, self.run_state, Mock(), save)
        self.assertIn("3 分钟", first)
        self.assertIn("仍未确认", second)
        self.assertEqual(self.run_state["applications"]["BBK"]["state"], "timed_out")
        submit.assert_called_once()
        signals.fortress_application_timeout.emit.assert_called_once_with("mumu:2:android:test", "test-2", first)

    def test_optional_inactive_alliance_warning_checks_box_then_cancels(self):
        lines = [
            line(280, 399, "温馨提示"), line(196, 514, "当前联盟的盟主暂时处于非活跃状"),
            line(276, 667, "该联盟不再提示"), line(171, 735, "取消"), line(412, 733, "退出联盟"),
        ]
        empty = Image.new("RGB", fortress.REFERENCE, (55, 68, 90))
        empty.paste((148, 178, 196), (230, 660, 263, 691))
        checked = empty.copy()
        checked.paste((246, 248, 251), (242, 667, 253, 678))
        target = Mock()
        before = (empty, empty, lines)
        after = (checked, checked, lines)
        with patch.object(fortress, "_alliance_frame", side_effect=[before, before, after, after]):
            fortress.dismiss_inactive_alliance_warning(target, Mock(), Event())
        self.assertEqual([call.args[0] for call in target.shell.call_args_list],
                         [["input", "tap", "246", "676"], ["input", "tap", "204", "745"]])
        target.shell.reset_mock()
        with patch.object(fortress, "_alliance_frame", side_effect=[after, after]):
            fortress.dismiss_inactive_alliance_warning(target, Mock(), Event())
        target.shell.assert_called_once_with(["input", "tap", "204", "745"], timeout=5)

    def test_wrong_modal_and_unconfirmed_checkbox_never_cancel(self):
        lines = [
            line(280, 399, "温馨提示"), line(196, 514, "当前联盟的盟主暂时处于非活跃状"),
            line(276, 667, "该联盟不再提示"), line(171, 735, "取消"), line(412, 733, "退出联盟"),
        ]
        empty = Image.new("RGB", fortress.REFERENCE, (55, 68, 90))
        empty.paste((148, 178, 196), (230, 660, 263, 691))
        target = Mock()
        with patch.object(fortress, "_alliance_frame", return_value=(empty, empty, lines)):
            with self.assertRaisesRegex(ValueError, "已勾选"):
                fortress.dismiss_inactive_alliance_warning(target, Mock(), Event())
        target.shell.assert_called_once_with(["input", "tap", "246", "676"], timeout=5)
        target.shell.reset_mock()
        with patch.object(fortress, "_alliance_frame", return_value=(empty, empty, lines[1:])):
            with self.assertRaises(ValueError):
                fortress.dismiss_inactive_alliance_warning(target, Mock(), Event())
        target.shell.assert_not_called()

    def test_direct_join_can_finish_without_any_popup(self):
        unaffiliated = [
            line(89, 21, "联盟"), line(77, 110, "建立联盟"), line(498, 112, "邀请/申请"),
            line(56, 196, "ZYZ"), line(190, 284, "[ ZYZ 示例联盟"), line(220, 357, "54/84"),
            line(526, 344, "加入"),
        ]
        joined = [
            line(89, 21, "联盟"), line(262, 101, "[ZYZ] 示例联盟"), line(262, 157, "盟主："),
            line(266, 190, "实力："), line(302, 223, "排名："), line(160, 1157, "成员"), line(314, 1157, "激励"),
        ]
        image = Image.new("RGB", fortress.REFERENCE, (40, 180, 66))
        first, second = (image, image, unaffiliated), (image, image, joined)
        target, remember = Mock(), Mock()
        with patch.object(fortress, "_alliance_frame", side_effect=[first, first, second, second]):
            fortress.join_available_alliance(target, Mock(), Event(), "ZYZ", remember)
        remember.assert_called_once()
        target.shell.assert_called_once_with(["input", "tap", "549", "353"], timeout=5)

    def test_activity_tab_anchor_is_position_independent_and_rejects_ambiguous_matches(self):
        lines = [line(10, 10, "常规活动")]
        screen = Image.new("RGB", fortress.REFERENCE, (49, 91, 135))
        self.assertIsNone(fortress.fortress_tab_point(screen, lines))
        asset = Image.fromarray(fortress._fortress_tab_image())
        screen.paste(asset, (360, 101), asset)
        self.assertEqual(fortress.fortress_tab_point(screen, lines), (402, 134))
        screen.paste(asset, (100, 101), asset)
        self.assertIsNone(fortress.fortress_tab_point(screen, lines))

    def test_navigation_requires_two_recognized_main_screen_frames(self):
        target = Mock()
        screen = Image.new("RGB", fortress.REFERENCE, (40, 180, 66))
        target.screenshot.return_value = screen
        lines = [
            line(47, 1164, "探险"), line(265, 1164, "背包"),
            line(373, 1164, "商店"), line(480, 1164, "联盟"),
        ]
        with patch.object(fortress, "root_entry", side_effect=[(620, 981), *([None] * 5)]):
            with self.assertRaises(ValueError):
                fortress.open_game_screen(target, Mock(side_effect=[lines, *([[]] * 5)]), Event(), "mail")
        target.shell.assert_not_called()

    def test_activity_swipe_is_not_replayed_without_movement(self):
        target = Mock()
        target.screenshot.return_value = Image.new("RGB", fortress.REFERENCE, (49, 91, 135))
        ocr = Mock(return_value=[line(10, 10, "常规活动"), line(110, 149, "巨熊行动")])
        with self.assertRaisesRegex(ValueError, "滑动未确认"):
            fortress.open_fortress_activity(target, ocr, Event())
        target.shell.assert_called_once()
        self.assertEqual(target.shell.call_args.args[0], ["input", "swipe", "113", "125", "287", "125", "460"])

    def test_disagreeing_reads_never_submit(self):
        target = Mock()
        pending = fortress.RewardMail(fortress.parse_stamp("2026-11-20 10:20:02"), "堡垒争夺胜利", False)
        record = Mock()
        with patch.object(fortress, "capture_reward", side_effect=[(None, pending), (None, None)]):
            with self.assertRaises(ValueError):
                fortress.collect_reward(target, Mock(), Event(), record, claim=True)
        target.shell.assert_not_called()
        record.assert_not_called()

    def test_pending_write_precedes_single_tap_and_unconfirmed_tap_is_not_replayed(self):
        target = Mock()
        frame = Image.new("RGB", fortress.REFERENCE, (40, 180, 66))
        now = fortress.parse_stamp("2026-11-20 10:20:02")
        pending = fortress.RewardMail(now, "堡垒争夺胜利", False)

        def record(mail, status):
            fortress.record_mail(self.run_state, "BBK", mail.stamp, status, now)

        def assert_intent(*args, **kwargs):
            self.assertEqual(self.run_state["mail"]["BBK"]["2026-11-20 10:20:02"], "pending")
        target.shell.side_effect = assert_intent
        with patch.object(fortress, "capture_reward", return_value=(frame, pending)):
            with self.assertRaisesRegex(ValueError, "结果未确认"):
                fortress.collect_reward(target, Mock(), Event(), record, claim=True)
            with self.assertRaisesRegex(ValueError, "已有领取记录"):
                fortress.collect_reward(target, Mock(), Event(), record, claim=True)
        target.shell.assert_called_once()
        acknowledged = fortress.RewardMail(now, pending.title, True)
        with patch.object(fortress, "capture_reward", return_value=(frame, acknowledged)):
            fortress.collect_reward(target, Mock(), Event(), record, claim=False)
        self.assertEqual(self.run_state["mail"]["BBK"]["2026-11-20 10:20:02"], "claimed")
        target.shell.assert_called_once()

    def test_verified_mail_reuses_frame_then_closes_only_after_claim_is_recorded(self):
        target, ocr, opened, confirmed, stop = Mock(), Mock(), Mock(), Mock(), Event()
        stamp = fortress.parse_stamp("2026-11-20 12:00:00")
        pending = fortress.RewardMail(stamp, "堡垒争夺胜利", False)
        claimed = fortress.RewardMail(stamp, pending.title, True)
        events = Mock()
        with (patch.object(fortress, "capture_reward", return_value=(confirmed, claimed)) as read,
              patch.object(fortress, "claim_reward", side_effect=events.tap)):
            self.assertEqual(fortress.collect_reward(
                target, ocr, stop, events.record, claim=True, verified=(opened, pending), on_claimed=events.close), claimed)
        read.assert_called_once_with(target, ocr)
        self.assertEqual([entry[0] for entry in events.mock_calls], ["record", "tap", "record", "close"])
        events.close.assert_called_once_with(confirmed)

    def test_profiles_are_isolated_and_stale_writes_are_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "routes.json"
            first, second = "mumu:2:android:aaaa", "mumu:0:android:bbbb"
            fortress.save_run(first, None, self.run_state, path)
            other = deepcopy(self.run_state)
            other["index"] = 1
            fortress.save_run(second, None, other, path)
            with self.assertRaises(ValueError):
                fortress.save_run(first, None, other, path)
            self.assertEqual(fortress.load_run(first, path), self.run_state)
            self.assertEqual(fortress.load_run(second, path), other)

    def test_switching_rounds_keeps_full_history_beyond_one_hundred(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "routes.json"
            identity, other = "mumu:2:android:aaaa", "mumu:0:android:bbbb"
            start = fortress.parse_stamp(self.run_state["round_start"])
            previous = None
            first = None
            for offset in range(102):
                run = deepcopy(self.run_state)
                stamp = fortress.format_stamp(start + timedelta(days=offset))
                run.update(round_start=stamp, index=len(run["route"]))
                run["mail"]["BBK"] = {stamp: "claimed"}
                run["keys"]["BBK"] = stamp
                fortress.save_run(identity, previous, run, path)
                if first is None:
                    first = run
                previous = run
            draft = deepcopy(self.run_state)
            draft["round_start"] = fortress.format_stamp(start + timedelta(days=102))
            fortress.save_run(identity, previous, draft, path)
            fortress.archive_run(identity, first, path)
            history = fortress.load_history(identity, path)
            self.assertEqual(len(history), 102)
            self.assertEqual((history[0], history[-1]), (previous, first))
            self.assertEqual(fortress.load_run(identity, path), draft)
            self.assertEqual(fortress.load_history(other, path), [])

    def test_completed_current_round_is_visible_and_updates_in_place(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "routes.json"
            identity = "mumu:2:android:aaaa"
            completed = deepcopy(self.run_state)
            completed["index"] = len(completed["route"])
            fortress.save_run(identity, None, completed, path)
            self.assertEqual(fortress.load_history(identity, path), [completed])
            updated = deepcopy(completed)
            updated["keys"]["BBK"] = "2026-11-20 10:50:01"
            fortress.save_run(identity, completed, updated, path)
            self.assertEqual(fortress.load_history(identity, path), [updated])
