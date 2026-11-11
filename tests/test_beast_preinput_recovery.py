import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from wjdr_backend import AdbError
from wjdr_beast_supervision import (InitialRecognitionTimeout, run_preinput_recovery,
                                    verify_bound_identity)


class Stop:
    def __init__(self):
        self.stopped = False
        self.waits = []

    def is_set(self):
        return self.stopped

    def wait(self, delay):
        self.waits.append(delay)
        return self.stopped


class PreinputRecoveryTest(unittest.TestCase):
    def run_case(self, job, target, stop, *, intent=True, pending=False, identity=True):
        events = []
        with patch('wjdr_beast_supervision.read_intent', return_value={'generation': 'g', 'running': intent}), \
             patch('wjdr_beast_supervision.token_matches', side_effect=lambda _intent, _generation: intent), \
             patch('wjdr_beast_supervision.has_unresolved_actions', return_value=pending):
            result = run_preinput_recovery(job, target, stop, 'account', 'g',
                                           lambda: identity, events.append)
        return result, events

    def test_recognition_timeout_retries_without_input(self):
        calls = []
        def job():
            calls.append(1)
            if len(calls) == 1:
                raise InitialRecognitionTimeout()
            return 'fresh recognition'
        stop = Stop()
        result, _ = self.run_case(job, SimpleNamespace(input_attempted=False), stop)
        self.assertEqual(result, 'fresh recognition')
        self.assertEqual(len(calls), 2)
        self.assertEqual(stop.waits, [0.2])

    def test_stop_changed_intent_pending_or_identity_blocks_retry(self):
        for options in ({'intent': False}, {'pending': True}, {'identity': False}):
            with self.subTest(options=options):
                calls = []
                def job():
                    calls.append(1)
                    raise InitialRecognitionTimeout()
                self.run_case(job, SimpleNamespace(input_attempted=False), Stop(), **options)
                self.assertEqual(len(calls), 1)
        stop = Stop()
        def stopped_job():
            stop.stopped = True
            raise InitialRecognitionTimeout()
        result, _ = self.run_case(stopped_job, SimpleNamespace(input_attempted=False), stop)
        self.assertIsNone(result)

    def test_unknown_input_acknowledgement_never_replayed(self):
        for error in (InitialRecognitionTimeout, AdbError):
            with self.subTest(error=error):
                calls = []
                def job():
                    calls.append(1)
                    raise error('unknown acknowledgement')
                with self.assertRaises(error):
                    self.run_case(job, SimpleNamespace(input_attempted=True), Stop())
                self.assertEqual(len(calls), 1)

    def test_adb_read_error_preserves_existing_preinput_retry(self):
        calls = []
        def job():
            calls.append(1)
            if len(calls) == 1:
                raise AdbError('capture failed')
            return 'ok'
        stop = Stop()
        result, _ = self.run_case(job, SimpleNamespace(input_attempted=False), stop)
        self.assertEqual(result, 'ok')
        self.assertEqual(stop.waits, [2.0])

    def test_unreadable_identity_waits_then_recovers_without_input(self):
        calls = []
        def job():
            calls.append(1)
            if len(calls) == 1:
                raise InitialRecognitionTimeout()
            return 'ok'
        verify = Mock(side_effect=[None, AdbError('temporarily unavailable'), True])
        stop = Stop()
        with patch('wjdr_beast_supervision.read_intent', return_value={}), \
             patch('wjdr_beast_supervision.token_matches', return_value=True), \
             patch('wjdr_beast_supervision.has_unresolved_actions', return_value=False):
            result = run_preinput_recovery(job, SimpleNamespace(input_attempted=False), stop,
                                           'account', 'g', verify, lambda _: None)
        self.assertEqual(result, 'ok')
        self.assertEqual(len(calls), 2)
        self.assertEqual(verify.call_count, 3)
        self.assertEqual(stop.waits, [0.2, 2.0, 2.0])

    def test_stop_intent_pending_and_mismatch_end_identity_wait(self):
        for condition in ('stop', 'intent', 'pending', 'mismatch'):
            with self.subTest(condition=condition):
                calls = []
                def job():
                    calls.append(1)
                    raise InitialRecognitionTimeout()
                class ControlledStop(Stop):
                    def wait(self, delay):
                        result = super().wait(delay)
                        if condition == 'stop' and delay == 2.0:
                            self.stopped = True
                            return True
                        return result
                verify = Mock(side_effect=[None, False] if condition == 'mismatch' else [None, True])
                intent = Mock(side_effect=[True, False] if condition == 'intent' else [True, True])
                pending = Mock(side_effect=[False, True] if condition == 'pending' else [False, False])
                with patch('wjdr_beast_supervision.read_intent', return_value={}), \
                     patch('wjdr_beast_supervision.token_matches', intent), \
                     patch('wjdr_beast_supervision.has_unresolved_actions', pending):
                    result = run_preinput_recovery(job, SimpleNamespace(input_attempted=False),
                        ControlledStop(), 'account', 'g', verify, lambda _: None)
                self.assertIsNone(result)
                self.assertEqual(len(calls), 1)
                self.assertEqual(verify.call_count, 2 if condition == 'mismatch' else 1)

    def test_bound_identity_distinguishes_unreadable_and_mismatch(self):
        expected = 'mumu:2:android:abc123'
        for players, actual, result in (
            ([], expected, None),
            ([object()], 'adb:127.0.0.1:16448', None),
            ([object()], 'android:abc123', None),
            ([object()], expected, True),
            ([object()], 'mumu:2:android:fedcba', False),
        ):
            with self.subTest(players=bool(players), actual=actual):
                fresh = SimpleNamespace(device_identities={'old': 'stale'},
                                        device_boot_ids={'old': 'stale'},
                                        _manager_players=lambda: players,
                                        device_identity=lambda _device: actual)
                adb = SimpleNamespace(clone_for_device=lambda _device: fresh)
                self.assertIs(verify_bound_identity(adb, 'serial', expected), result)
                self.assertEqual(fresh.device_identities, {})
                self.assertEqual(fresh.device_boot_ids, {})


if __name__ == '__main__':
    unittest.main()
