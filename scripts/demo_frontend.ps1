param([ValidateRange(0, 9)][int]$Page = 4, [string]$Screenshot = '')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$python = (Get-Command pythonw.exe -ErrorAction Stop).Source
$env:WJDR_QA_PAGE = [string]$Page
if ($Screenshot) { $env:WJDR_QA_SCREENSHOT = [IO.Path]::GetFullPath($Screenshot) }
# Never pass auto-task arguments or terminate an existing worker for a demo.
$timer = [Diagnostics.Stopwatch]::StartNew()
$process = Start-Process -FilePath $python -ArgumentList 'wjdr_mumu_assistant_qt.py' -WorkingDirectory $repo -WindowStyle Normal -PassThru
$deadline = [DateTime]::UtcNow.AddSeconds(15)
while ([DateTime]::UtcNow -lt $deadline) {
    $process.Refresh()
    if ($process.HasExited) { throw "Frontend exited: $($process.ExitCode)" }
    if ($process.MainWindowHandle -ne 0 -and $process.MainWindowTitle) {
        Write-Output "Frontend ready in $([Math]::Round($timer.Elapsed.TotalSeconds, 2))s; PID $($process.Id); $($process.MainWindowTitle)"
        exit 0
    }
    Start-Sleep -Milliseconds 100
}
if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
throw 'Frontend startup exceeded 15 seconds; stopped only this demo process.'
