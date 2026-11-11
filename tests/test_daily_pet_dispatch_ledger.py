from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wjdr_backend import PetDispatchLedger


def test_pet_intent_is_account_scoped_and_crash_safe():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        account = "mumu:2:android:example2"
        first = PetDispatchLedger(account, "2026-11-10", root)
        assert first.available() and first.reserve()
        assert not first.available()
        # A new process cannot confirm or repeat an unknown acknowledgement,
        # even when the date changes.
        restarted = PetDispatchLedger(account, "2026-11-11", root)
        assert not restarted.available() and not restarted.reserve() and not restarted.confirm()
        other = PetDispatchLedger("mumu:0:android:example0", "2026-11-10", root)
        assert other.available()
        assert first.confirm() and not first.available()
        assert PetDispatchLedger(account, "2026-11-11", root).available()
        # A clock rollback cannot make a future-day record eligible.
        assert not PetDispatchLedger(account, "2026-11-09", root).available()


def test_corrupt_or_unstable_identity_fails_closed():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        ledger = PetDispatchLedger("mumu:2:android:example2", "2026-11-10", root)
        ledger.path.write_text("{bad json", encoding="utf-8")
        assert not ledger.available() and not ledger.reserve()
        try:
            PetDispatchLedger("adb:127.0.0.1:16448", "2026-11-10", root)
        except ValueError:
            pass
        else:
            raise AssertionError("an unstable device identity must be rejected")


if __name__ == "__main__":
    test_pet_intent_is_account_scoped_and_crash_safe()
    test_corrupt_or_unstable_identity_fails_closed()
    print("pet dispatch ledger: PASS")
