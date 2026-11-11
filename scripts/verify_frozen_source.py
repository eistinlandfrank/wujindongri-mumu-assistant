"""Verify the actual frozen modules/assets, not just embedded version strings."""
from pathlib import Path
import marshal
import sys
from PyInstaller.archive.readers import CArchiveReader

repo = Path(__file__).resolve().parents[1]
runtime = Path(sys.argv[1]).resolve()
archive = CArchiveReader(str(runtime / "WJDRMuMuAssistant.exe"))
pyz = archive.open_embedded_archive("PYZ.pyz")
modules = ("wjdr_mumu_assistant_qt", "wjdr_backend", "wjdr_beast_hunt",
           "wjdr_schedule", "wjdr_schedule_ui", "wjdr_daily_controller",
           "wjdr_ui_components", "wjdr_runtime_config", "wjdr_frontend_layout",
           "wjdr_beast_supervision", "wjdr_daily_visuals",
           "wjdr_daily_intel", "wjdr_daily_expedition", "wjdr_scoreboard",
           "wjdr_scoreboard_ui")
if (repo / "wjdr_scoreboard_identity.py").is_file():
    modules += ("wjdr_scoreboard_identity",)
for name in modules:
    code = (marshal.loads(archive.extract(name)) if name == modules[0] else pyz.extract(name))
    expected = compile((repo / (name + ".py")).read_bytes(), code.co_filename,
                       "exec", dont_inherit=True, optimize=0)
    assert code == expected, f"stale frozen source: {name}"
assert (runtime / "wjdr_fast_vision.py").read_bytes() == (repo / "wjdr_fast_vision.py").read_bytes(), "stale standalone recognizer"
assets = list((repo / "assets").glob("*"))
for source in assets:
    if source.is_file():
        assert source.read_bytes() == (runtime / "_internal" / "assets" / source.name).read_bytes(), source.name
print(f"PASS {len(modules)} current frozen modules and all asset bytes")
