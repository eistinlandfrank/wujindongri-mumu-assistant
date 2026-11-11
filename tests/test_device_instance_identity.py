from __future__ import annotations

from wjdr_backend import MuMuADB


def test_manager_does_not_inherit_assistant_qt_overrides():
    from unittest.mock import patch
    import wjdr_backend

    overrides = {'QT_QPA_PLATFORM': 'offscreen', 'QT_QPA_PLATFORM_PLUGIN_PATH': 'wrong-plugins', 'QT_PLUGIN_PATH': 'wrong-plugins'}
    with patch.dict(wjdr_backend.os.environ, overrides), patch.object(wjdr_backend.subprocess, 'run') as run:
        run.return_value.stdout = b'[]'
        adb = MuMuADB.__new__(MuMuADB)
        adb.manager_path = 'MuMuManager.exe'
        assert adb._manager_players() == []
        env = run.call_args.kwargs['env']
        assert not any(k.upper().startswith('QT_QPA_') or k.upper() in {'QT_PLUGIN_PATH', 'QT_CONF_PATH'} for k in env)
        assert env.get('PATH') == wjdr_backend.os.environ.get('PATH')


class FakeMuMuADB(MuMuADB):
    def __init__(self) -> None:
        self.adb_path = "fake-adb"
        self.manager_path = "fake-manager"
        self.device = ""
        self.players = [
            {
                "index": "0",
                "adb_host_ip": "127.0.0.1",
                "adb_port": 25600,
                "is_process_started": True,
            },
            {
                "index": "2",
                "adb_host_ip": "127.0.0.1",
                "adb_port": 25664,
                "is_process_started": True,
            },
        ]
        self.device_identities = {}
        self.device_boot_ids = {}
        self.android_ids = {
            "127.0.0.1:25600": "same-cloned-id",
            "127.0.0.1:5555": "same-cloned-id",
            "127.0.0.1:25664": "same-cloned-id",
            "127.0.0.1:5559": "same-cloned-id",
        }
        self.boot_ids = {
            "127.0.0.1:25600": "11111111-1111-1111-1111-111111111111",
            "127.0.0.1:5555": "11111111-1111-1111-1111-111111111111",
            "127.0.0.1:25664": "22222222-2222-2222-2222-222222222222",
            "127.0.0.1:5559": "22222222-2222-2222-2222-222222222222",
        }

    def _run(
        self,
        args: list[str],
        timeout: float = 20,
        binary: bool = False,
    ) -> bytes | str:
        del timeout, binary
        serial = args[1]
        if args[-3:] == ["get", "secure", "android_id"]:
            return self.android_ids[serial] + "\n"
        if args[-1] == "/proc/sys/kernel/random/boot_id":
            return self.boot_ids[serial] + "\n"
        raise AssertionError(f"unexpected fake ADB command: {args!r}")


def test_cloned_android_ids_stay_distinct_per_mumu_instance() -> None:
    adb = FakeMuMuADB()

    original = adb.device_identity("127.0.0.1:25600")
    clone = adb.device_identity("127.0.0.1:25664")

    assert original == "mumu:0:android:same-cloned-id"
    assert clone == "mumu:2:android:same-cloned-id"
    assert original != clone


def test_each_adb_alias_uses_its_own_manager_instance_identity() -> None:
    adb = FakeMuMuADB()

    assert adb.device_identity("127.0.0.1:5555") == adb.device_identity(
        "127.0.0.1:25600"
    )
    assert adb.device_identity("127.0.0.1:5559") == adb.device_identity(
        "127.0.0.1:25664"
    )
    assert adb.device_identity("127.0.0.1:5555") != adb.device_identity(
        "127.0.0.1:5559"
    )


def test_transient_missing_android_id_is_retried_and_not_cached() -> None:
    adb = FakeMuMuADB()
    real_run = adb._run
    failures = {"remaining": 2}

    def flaky_run(args: list[str], timeout: float = 20, binary: bool = False):
        if args[-3:] == ["get", "secure", "android_id"] and failures["remaining"]:
            failures["remaining"] -= 1
            return "null\n"
        return real_run(args, timeout=timeout, binary=binary)

    adb._run = flaky_run  # type: ignore[method-assign]
    assert adb.device_identity("127.0.0.1:25600") == "mumu:0"
    assert "127.0.0.1:25600" not in adb.device_identities
    assert adb.device_identity("127.0.0.1:25600") == (
        "mumu:0:android:same-cloned-id"
    )
