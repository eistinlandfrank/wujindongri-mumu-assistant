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
           "wjdr_schedule", "wjdr_schedule_ui")
for name in modules:
    code = (marshal.loads(archive.extract(name)) if name == modules[0] else pyz.extract(name))
    expected = compile((repo / (name + ".py")).read_bytes(), code.co_filename,
                       "exec", dont_inherit=True, optimize=0)
    assert code == expected, f"stale frozen source: {name}"
assets = list((repo / "assets").glob("*"))
for source in assets:
    if source.is_file():
        assert source.read_bytes() == (runtime / "_internal" / "assets" / source.name).read_bytes(), source.name
print(f"PASS {len(modules)} current frozen modules and all asset bytes")
