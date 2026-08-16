param(
    [string]$OutputRoot = (Join-Path $PSScriptRoot "release"),
    [switch]$Incremental
)

$ErrorActionPreference = "Stop"
$appName = "WJDRMuMuAssistant"
$assets = @(
    "alliance_all_help_builtin.png",
    "alliance_help_builtin.png",
    "alliance_mutual_page_builtin.png",
    "alliance_mutual_entry_builtin.png",
    "alliance_city_entry_builtin.png",
    "app_icon.svg"
)

$arguments = @(
    "--noconfirm", "--windowed",
    "--name", $appName,
    "--icon", (Join-Path $PSScriptRoot "app_icon.ico"),
    "--version-file", (Join-Path $PSScriptRoot "version_info.txt"),
    "--distpath", (Join-Path $OutputRoot "dist"),
    "--workpath", (Join-Path $OutputRoot "work"),
    "--specpath", (Join-Path $OutputRoot "spec"),
    (Join-Path $PSScriptRoot "wjdr_mumu_assistant_qt.py")
)

if (-not $Incremental) {
    $arguments = @("--clean") + $arguments
}

foreach ($asset in $assets) {
    $arguments += "--add-data"
    $arguments += "$(Join-Path $PSScriptRoot $asset);."
}

# The red-packet workflow loads its reviewed anchors from an ``assets``
# directory.  Preserve that relative directory inside the portable package.
$arguments += "--add-data"
$arguments += "$(Join-Path $PSScriptRoot 'assets');assets"

& python -m PyInstaller @arguments
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$packageRoot = Join-Path (Join-Path $OutputRoot "dist") $appName
foreach ($document in (Get-ChildItem -LiteralPath $PSScriptRoot -File | Where-Object {
    $_.Extension -in @(".md", ".txt", ".cmd") -and $_.Name -notin @("SHA256.txt", "version_info.txt", "requirements.txt")
})) {
    Copy-Item -LiteralPath $document.FullName -Destination $packageRoot -Force
}

# Keep the read-only batch recogniser usable beside the portable GUI.  It is
# intentionally a source-mode diagnostic (the host needs Python plus the
# small requirements file) and has no input commands; copying both modules
# fixes the old package where 快速识图.cmd was present but its target script
# was missing.
foreach ($toolFile in @("wjdr_fast_vision.py", "wjdr_backend.py", "requirements.txt")) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $toolFile) -Destination $packageRoot -Force
}
foreach ($asset in $assets) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $asset) -Destination $packageRoot -Force
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "assets") -Destination $packageRoot -Recurse -Force

Write-Host "Portable release staged at: $packageRoot"
