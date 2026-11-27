param(
    [string]$OutputRoot = "release",
    [switch]$Incremental
)

$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$OutputRoot = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputRoot)
$appName = "WJDRMuMuAssistant"
$sources = Join-Path $repo "src"
$assets = Join-Path $repo "assets"
$arguments = @(
    "--noconfirm", "--windowed",
    "--name", $appName,
    "--icon", (Join-Path $assets "app_icon.ico"),
    "--version-file", (Join-Path $PSScriptRoot "version_info.txt"),
    "--distpath", (Join-Path $OutputRoot "dist"),
    "--workpath", (Join-Path $OutputRoot "work"),
    "--specpath", (Join-Path $OutputRoot "spec"),
    "--collect-all", "onnxruntime",
    "--add-data", "${assets};assets",
    (Join-Path $sources "wjdr_mumu_assistant_qt.py")
)
if (-not $Incremental) {
    $arguments = @("--clean") + $arguments
}

& python -m PyInstaller @arguments
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$packageRoot = Join-Path $OutputRoot "dist/$appName"
# Avoid shadowing the Windows ICU exports expected by Qt 6.11.
$internalRoot = Join-Path $packageRoot "_internal"
foreach ($icuName in @("icuuc.dll", "icudt78.dll")) {
    $icuPath = Join-Path $internalRoot $icuName
    if (Test-Path -LiteralPath $icuPath) { Remove-Item -LiteralPath $icuPath -Force }
}

# Stage the standalone diagnostic sources beside the frozen app.
$sourceCopy = Join-Path $packageRoot "src"
[void][IO.Directory]::CreateDirectory($sourceCopy)
Get-ChildItem -LiteralPath $sources -File -Filter "wjdr_*.py" | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $sourceCopy -Force
}
Copy-Item -LiteralPath (Join-Path $repo "requirements.txt") -Destination $packageRoot -Force
Copy-Item -LiteralPath $assets -Destination $packageRoot -Recurse -Force

Write-Host "Portable release staged at: $packageRoot"
