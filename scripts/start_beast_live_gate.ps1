param([Parameter(Mandatory=$true)][string]$Device)
$ErrorActionPreference='Stop'
if ($Device -notmatch '^127\.0\.0\.1:\d+$') {throw 'Explicit local ADB required'}
$repo=Split-Path $PSScriptRoot -Parent
$env:WJDR_QA_PAGE='4'
Remove-Item Env:WJDR_BEAST_MAX_CYCLES -ErrorAction SilentlyContinue
Remove-Item Env:WJDR_BEAST_SEARCH_RACE_PAUSE -ErrorAction SilentlyContinue
# User requested actual Beast recovery. Normal continuous mode, no QA cap.
$process=Start-Process -FilePath (Get-Command pythonw.exe).Source -ArgumentList 'wjdr_mumu_assistant_qt.py','--device',$Device,'--auto-beast-rally' -WorkingDirectory $repo -WindowStyle Normal -PassThru
$deadline=[DateTime]::UtcNow.AddSeconds(15)
while([DateTime]::UtcNow -lt $deadline) {
  $process.Refresh()
  if($process.HasExited){throw 'Frontend failed'}
  if($process.MainWindowHandle -and $process.MainWindowTitle){Write-Output "PID $($process.Id): $($process.MainWindowTitle)"; exit 0}
  Start-Sleep -Milliseconds 100
}
& taskkill.exe /PID $process.Id /T /F
throw 'Startup exceeded15s'
