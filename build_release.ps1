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
# Qt 6.11 imports Windows' unversioned ICU exports. PyInstaller can pick a
# PATH application's renamed ICU (e.g. ucnv_open_78), which breaks QtCore on
# startup. Do not ship that shadowing copy; supported Windows supplies ICU.
$internalRoot = [IO.Path]::GetFullPath((Join-Path $packageRoot '_internal'))
foreach ($icuName in @('icuuc.dll', 'icudt78.dll')) {
    $icuPath = [IO.Path]::GetFullPath((Join-Path $internalRoot $icuName))
    if ([IO.Path]::GetDirectoryName($icuPath) -ne $internalRoot) { throw 'Invalid runtime ICU path' }
    if (Test-Path -LiteralPath $icuPath) { Remove-Item -LiteralPath $icuPath -Force }
}
foreach ($document in @('README.md', '第三方许可说明.txt', '快速识图工具.md', '快速识图.cmd')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $document) -Destination $packageRoot -Force
}

# Keep the read-only batch recogniser usable beside the portable GUI.  It is
# intentionally a source-mode diagnostic (the host needs Python plus the
# small requirements file). Ship its source imports and the IPC worker beside it.
foreach ($module in (Get-ChildItem -LiteralPath $PSScriptRoot -File -Filter "wjdr_*.py")) {
    Copy-Item -LiteralPath $module.FullName -Destination $packageRoot -Force
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "requirements.txt") -Destination $packageRoot -Force
foreach ($asset in $assets) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $asset) -Destination $packageRoot -Force
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "assets") -Destination $packageRoot -Recurse -Force

Write-Host "Portable release staged at: $packageRoot"
