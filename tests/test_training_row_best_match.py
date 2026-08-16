from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PIL import Image

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import wjdr_backend as backend  # noqa: E402
from wjdr_backend import DailyMissionKind  # noqa: E402


def main() -> None:
    frame = Image.new("RGB", (1440, 2560), (224, 229, 243))

    def fake_title_match(_image, _asset, template_name, _threshold, _region):
        if "shield_30_20" in template_name:
            return (369, 1042), 0.9762
        if "spear_30_20" in template_name:
            return (369, 1042), 0.9993
        if "archer_30_10" in template_name:
            return (369, 1352), 0.9968
        return None, 0.0

    def fake_go_match(_image, _threshold, region):
        row_center = round((region[1] + region[3]) / 2)
        return (1165, 1155 if row_center < 1200 else 1465), 1.0

    with patch.object(backend, "_match_daily_task_template", fake_title_match), patch.object(
        backend,
        "_match_daily_mission_go_control",
        fake_go_match,
    ):
        matches = backend.match_daily_training_missions(frame, 0.94)

    assert [(item.kind, item.go_point) for item in matches] == [
        (DailyMissionKind.TRAIN_SPEAR, (1165, 1155)),
        (DailyMissionKind.TRAIN_ARCHER, (1165, 1465)),
    ]
    assert matches[0].score == 0.9993
    print("training same-row best-title selection: PASS")


if __name__ == "__main__":
    main()
