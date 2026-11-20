param([string]$OutputRoot="release",[switch]$SkipRuntime)
$ErrorActionPreference="Stop"
$repo=Split-Path $PSScriptRoot -Parent
Set-Location $repo
$OutputRoot = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputRoot)
if(-not $SkipRuntime) {
    & python scripts\run_bounded.py --seconds 25 powershell -NoProfile -ExecutionPolicy Bypass -File build_release.ps1 -OutputRoot $OutputRoot -Incremental
    if($LASTEXITCODE -ne 0){throw "Runtime build failed"}
}
$runtime=Join-Path $OutputRoot 'dist\WJDRMuMuAssistant'
& python scripts\run_bounded.py --seconds 22 python scripts\verify_frozen_source.py $runtime
if($LASTEXITCODE -ne 0){throw "Runtime does not match the current source"}
$payload=Join-Path $OutputRoot 'portable_payload'
& python scripts\run_bounded.py --seconds 25 python packaging\make_portable_payload.py $runtime $payload
if($LASTEXITCODE -ne 0){throw "Payload generation failed"}
$compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$output=Join-Path $OutputRoot 'WJDRMuMuAssistant_v5.8.0_Portable.exe'
& python scripts\run_bounded.py --seconds 25 $compiler /nologo /target:winexe /platform:x64 /optimize+ /win32icon:app_icon.ico /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll "/resource:$payload\payload.zip,payload.zip" "/resource:$payload\payload.sha256,payload.sha256" "/resource:$payload\files.sha256,files.sha256" "/out:$output" packaging\PortableLauncher.cs
if($LASTEXITCODE -ne 0){throw "Portable compile failed"}
& python -c "import hashlib,sys; print(hashlib.file_digest(open(sys.argv[1],'rb'),'sha256').hexdigest(),sys.argv[1])" $output
if($LASTEXITCODE -ne 0){throw "Portable hashing failed"}
