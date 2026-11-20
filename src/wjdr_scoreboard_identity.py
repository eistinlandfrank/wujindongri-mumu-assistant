"""Fresh, stable account binding for leaderboard input."""
import re


def verify_bound_identity(adb, device: str, expected_identity: str) -> bool | None:
    if not isinstance(expected_identity, str) or not re.fullmatch(r'mumu:[0-9]+:android:[0-9a-f]+', expected_identity):
        return False
    fresh = adb.clone_for_device(device)
    fresh.device_identities.clear()
    fresh.device_boot_ids.clear()
    fresh.players = fresh._manager_players()
    if not fresh.players:
        return None
    actual = fresh.device_identity(device)
    if not isinstance(actual, str) or not re.fullmatch(r'mumu:[0-9]+:android:[0-9a-f]+', actual):
        return None
    return actual == expected_identity
