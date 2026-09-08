param([Parameter(Mandatory=$true)][string]$Device)
$ErrorActionPreference='Stop'
if ($Device -notmatch '^127\.0\.0\.1:\d+$') {throw 'Explicit local ADB required'}
$repo=Split-Path $PSScriptRoot -Parent
$process=Start-Process -FilePath (Get-Command pythonw.exe).Source -ArgumentList 'scripts/live_conflict_transition_gate.py','--device',$Device,'--auto-beast-rally' -WorkingDirectory $repo -WindowStyle Normal -PassThru
$deadline=[DateTime]::UtcNow.AddSeconds(15)
while([DateTime]::UtcNow -lt $deadline) {
  $process.Refresh()
  if($process.HasExited){throw 'Frontend failed'}
  if($process.MainWindowHandle -and $process.MainWindowTitle){Write-Output "PID $($process.Id): $($process.MainWindowTitle)"; exit 0}
  Start-Sleep -Milliseconds 100
}
& taskkill.exe /PID $process.Id /T /F
throw 'Startup exceeded15s'
