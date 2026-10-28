"""Create a new runtime from a verified prior PyInstaller build, replacing changed modules.

The output must subsequently pass verify_frozen_source.py and actual boot testing.
Never modifies the input executable.
"""
import marshal
from pathlib import Path
import shutil
import struct
import sys
import zlib

from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.archive.writers import CArchiveWriter

repo = Path(__file__).resolve().parents[1]
source = (repo / 'release_v5_68/dist/WJDRMuMuAssistant').resolve()
target = (repo / 'release_v5_69/dist/WJDRMuMuAssistant').resolve()
assert source != target and source.is_dir()
original = source / 'WJDRMuMuAssistant.exe'
if target.exists():
    assert (target / original.name).read_bytes() == original.read_bytes(), 'Unexpected existing runtime'
else:
    shutil.copytree(source, target)
archive = CArchiveReader(str(original))
pyz = archive.open_embedded_archive('PYZ.pyz')
pyz_bytes = bytearray(archive.extract('PYZ.pyz'))
toc = dict(pyz.toc)
for name in ('wjdr_backend', 'wjdr_beast_hunt'):
    old_code = pyz.extract(name)
    code = compile((repo / (name + '.py')).read_bytes(), old_code.co_filename,
                   'exec', dont_inherit=True, optimize=0)
    blob = zlib.compress(marshal.dumps(code), 6)
    offset = len(pyz_bytes)
    pyz_bytes.extend(blob)
    toc[name] = (toc[name][0], offset, len(blob))
toc_offset = len(pyz_bytes)
pyz_bytes.extend(marshal.dumps(list(toc.items())))
pyz_bytes[8:12] = struct.pack('!i', toc_offset)

data = original.read_bytes()
cookie_at = archive._end_offset - archive._COOKIE_LENGTH
magic, _, old_toc_offset, _, pyvers, pylib = struct.unpack(
    archive._COOKIE_FORMAT, data[cookie_at:archive._end_offset])
prefix = data[:archive._start_offset]
payload = data[archive._start_offset:archive._start_offset + old_toc_offset]
new_offset = len(payload)
payload += pyz_bytes
entries = [(0, 0, 0, 0, 'o', option) for option in archive.options]
for name, (pos, length, raw_length, compressed, kind) in archive.toc.items():
    if name == 'PYZ.pyz':
        assert not compressed and kind == 'z'
        pos, length, raw_length = new_offset, len(pyz_bytes), len(pyz_bytes)
    entries.append((pos, length, raw_length, compressed, kind, name))
table = CArchiveWriter._serialize_toc(entries)
cookie = struct.pack(archive._COOKIE_FORMAT, magic,
                     len(payload) + len(table) + archive._COOKIE_LENGTH,
                     len(payload), len(table), pyvers, pylib)
(target / original.name).write_bytes(prefix + payload + table + cookie)
print('Incremental runtime prepared:', target)
