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
entry = "wjdr_mumu_assistant_qt"
modules = sorted(path.stem for path in sources.glob("wjdr_*.py"))
for name in modules:
    code = marshal.loads(archive.extract(name)) if name == entry else pyz.extract(name)
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
