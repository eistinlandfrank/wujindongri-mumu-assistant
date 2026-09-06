"""Generate ZIP+integrity manifests for the offline portable launcher."""
import argparse, hashlib, threading, os, zipfile, shutil
from pathlib import Path
guard=threading.Timer(295,lambda:os._exit(124));guard.daemon=True;guard.start()
p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
for name in ('README.md','发行说明.txt','第三方许可说明.txt'):
    shutil.copy2(Path(__file__).resolve().parents[1]/name,a.runtime/name)
files=sorted(path for path in a.runtime.rglob('*') if path.is_file() and (
    path.relative_to(a.runtime).parts[0]=='_internal' or
    path.relative_to(a.runtime).as_posix() in ('WJDRMuMuAssistant.exe','README.md','第三方许可说明.txt','发行说明.txt')
))
with zipfile.ZipFile(a.output/'payload.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
    lines=[]
    for path in files:
        relative=path.relative_to(a.runtime).as_posix()
        archive.write(path,relative)
        lines.append(hashlib.sha256(path.read_bytes()).hexdigest().upper()+'\t'+relative)
(a.output/'files.sha256').write_text('\n'.join(lines),encoding='utf-8')
digest=hashlib.sha256((a.output/'payload.zip').read_bytes()).hexdigest().upper()
(a.output/'payload.sha256').write_text(digest,encoding='ascii')
print('payload',len(files),'files', (a.output/'payload.zip').stat().st_size,'bytes',digest)
guard.cancel()
