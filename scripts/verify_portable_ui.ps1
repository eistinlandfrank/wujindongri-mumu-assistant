param([string]$OutputRoot = 'release_v5_66', [string]$Device = '')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$release = [IO.Path]::GetFullPath((Join-Path $repo $OutputRoot))
$exe = Join-Path $release 'WJDRMuMuAssistant_v5.66.0_Portable.exe'
$digest = (Get-Content -LiteralPath (Join-Path $release 'portable_payload/payload.sha256') -Raw).Trim()
$runtime = Join-Path $env:LOCALAPPDATA ("WJDRMuMuAssistant/portable/5.66.0-" + $digest.Substring(0,12))
$env:WJDR_QA_PAGE = '4'
$env:WJDR_QA_SCREENSHOT = Join-Path $repo 'evidence/milestone-183-owned-disappearance/portable-boot.png'
$watch = [Diagnostics.Stopwatch]::StartNew()
# A visible frontend is explicitly requested. Launch without task flags,
# from a non-source working directory; the package supplies its own runtime.
if ($Device) {
    $env:WJDR_QA_SCREENSHOT = Join-Path $repo 'evidence/milestone-183-owned-disappearance/portable-second.png'
    $launcher = Start-Process -FilePath (Join-Path $runtime 'WJDRMuMuAssistant.exe') -ArgumentList '--device',$Device -WorkingDirectory $env:TEMP -WindowStyle Normal -PassThru
} else {
    $launcher = Start-Process -FilePath $exe -WorkingDirectory $env:TEMP -WindowStyle Normal -PassThru
}
$deadline = [DateTime]::UtcNow.AddSeconds(20)
while ([DateTime]::UtcNow -lt $deadline) {
    $launcher.Refresh()
    $windows = @(Get-Process -Name WJDRMuMuAssistant -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -eq (Join-Path $runtime 'WJDRMuMuAssistant.exe') -and $_.MainWindowTitle -like '*5.66.0*127.0.0.1:*' -and
        ((-not $Device) -or ($_.Id -eq $launcher.Id -and $_.MainWindowTitle.EndsWith($Device)))
    })
    if ($windows.Count -gt 0) {
        if (-not (Test-Path -LiteralPath (Join-Path $runtime 'portable-verification.log'))) { throw 'Missing integrity verification' }
        Write-Output "PASS one-click portable boot: $([Math]::Round($watch.Elapsed.TotalSeconds,2))s"
        $windows | Select-Object Id,MainWindowTitle,Path
        exit 0
    }
    if ($launcher.HasExited -and $launcher.ExitCode -ne 0) { throw "Portable failed: $($launcher.ExitCode)" }
    Start-Sleep -Milliseconds 100
}
if (-not $launcher.HasExited) { & taskkill.exe /PID $launcher.Id /T /F | Out-Null }
throw 'Portable UI deadline exceeded 20s'
