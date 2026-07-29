param(
    [string]$OutputRoot = (Join-Path $PSScriptRoot "release")
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
    "--noconfirm", "--clean", "--windowed",
    "--name", $appName,
    "--icon", (Join-Path $PSScriptRoot "app_icon.ico"),
    "--version-file", (Join-Path $PSScriptRoot "version_info.txt"),
    "--distpath", (Join-Path $OutputRoot "dist"),
    "--workpath", (Join-Path $OutputRoot "work"),
    "--specpath", (Join-Path $OutputRoot "spec"),
    (Join-Path $PSScriptRoot "wjdr_mumu_assistant_qt.py")
)

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

Write-Host "Portable release staged at: $packageRoot"
