# Watches this folder and automatically commits + pushes every change to GitHub.
# Also pulls every few minutes so changes made on another PC arrive here.
# Log: autosync.log (in this folder). Stop: close the window, or end the "powershell" task.

$repo  = $PSScriptRoot
$quiet = 10      # seconds with no new changes before committing
$pullEvery = 300 # seconds between background pulls
$log   = Join-Path $repo "autosync.log"

$git = (Get-Command git -ErrorAction SilentlyContinue).Source
if (-not $git) { $git = "C:\Program Files\Git\cmd\git.exe" }
Set-Location $repo

function Log($msg) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg" | Out-File -Append -Encoding utf8 $log }
function Git { & $git @args 2>&1 | ForEach-Object { "$_" } }

function Sync-Pull {
  $out = Git pull --rebase --autostash
  if ($LASTEXITCODE -ne 0) { Git rebase --abort | Out-Null; Log "PULL FAILED (conflict?) - fix manually: $out"; return $false }
  return $true
}

function Sync-Push {
  Git add -A | Out-Null
  & $git diff --cached --quiet
  if ($LASTEXITCODE -ne 0) {
    Git commit -m "Auto-sync from $env:COMPUTERNAME $(Get-Date -Format 'yyyy-MM-dd HH:mm')" | Out-Null
    Log "Committed local changes"
  }
  if (-not (Sync-Pull)) { return }
  $ahead = Git rev-list --count "@{u}..HEAD"
  if ([int]$ahead -gt 0) {
    $out = Git push
    if ($LASTEXITCODE -eq 0) { Log "Pushed $ahead commit(s)" } else { Log "PUSH FAILED: $out" }
  }
}

$w = New-Object IO.FileSystemWatcher $repo
$w.IncludeSubdirectories = $true
$w.NotifyFilter = 'FileName, DirectoryName, LastWrite, Size'

Log "Auto-sync started for $repo"
Sync-Push
$dirty = $false; $lastChange = Get-Date; $lastPull = Get-Date

while ($true) {
  $r = $w.WaitForChanged([IO.WatcherChangeTypes]::All, 2000)
  if (-not $r.TimedOut) {
    $n = "$($r.Name)"
    if ($n -notmatch '^\.git([\\/]|$)' -and $n -ne 'autosync.log') { $dirty = $true; $lastChange = Get-Date }
  }
  $now = Get-Date
  if ($dirty -and ($now - $lastChange).TotalSeconds -ge $quiet) {
    $dirty = $false; Sync-Push; $lastPull = $now
  } elseif (-not $dirty -and ($now - $lastPull).TotalSeconds -ge $pullEvery) {
    $lastPull = $now
    $before = Git rev-parse HEAD
    if (Sync-Pull) { if ((Git rev-parse HEAD) -ne $before) { Log "Pulled changes from GitHub" } }
  }
}
