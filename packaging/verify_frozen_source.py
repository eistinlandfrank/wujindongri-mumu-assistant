"""Verify the actual frozen modules/assets, not just embedded version strings."""
from pathlib import Path
import marshal
import sys
from PyInstaller.archive.readers import CArchiveReader

repo = Path(__file__).resolve().parents[1]
sources = repo / "src"
runtime = Path(sys.argv[1]).resolve()
archive = CArchiveReader(str(runtime / "WJDRMuMuAssistant.exe"))
pyz = archive.open_embedded_archive("PYZ.pyz")
modules = ("wjdr_mumu_assistant_qt", "wjdr_backend", "wjdr_beast_hunt",
           "wjdr_schedule", "wjdr_schedule_ui", "wjdr_daily_controller",
           "wjdr_ui_components", "wjdr_runtime_config", "wjdr_frontend_layout",
           "wjdr_beast_supervision", "wjdr_daily_visuals",
           "wjdr_daily_intel", "wjdr_daily_expedition", "wjdr_scoreboard",
           "wjdr_scoreboard_ui", "wjdr_mumu_ipc", "wjdr_ui_appearance",
           "wjdr_fortress", "wjdr_fortress_flow", "wjdr_fortress_ocr", "wjdr_fortress_ui",
           "wjdr_bear", "wjdr_bear_ui")
if (sources / "wjdr_adb.py").is_file():
    modules += ("wjdr_adb",)
if (sources / "wjdr_scoreboard_identity.py").is_file():
    modules += ("wjdr_scoreboard_identity",)
for name in modules:
    code = (marshal.loads(archive.extract(name)) if name == modules[0] else pyz.extract(name))
    expected = compile((sources / (name + ".py")).read_bytes(), code.co_filename,
                       "exec", dont_inherit=True, optimize=0)
    assert code == expected, f"stale frozen source: {name}"
for name in ("wjdr_fast_vision.py", "wjdr_mumu_ipc.py"):
    assert (runtime / "src" / name).read_bytes() == (sources / name).read_bytes(), name
internal = runtime / "_internal"
assets = {path.relative_to(repo / "assets") for path in (repo / "assets").rglob("*") if path.is_file()}
packaged_assets = {path.relative_to(internal / "assets") for path in (internal / "assets").rglob("*") if path.is_file()}
assert packaged_assets == assets, "unexpected or missing packaged assets"
for relative in assets:
    assert (repo / "assets" / relative).read_bytes() == (internal / "assets" / relative).read_bytes(), relative
print(f"PASS {len(modules)} current frozen modules and all asset bytes")
