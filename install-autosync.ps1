# Makes autosync.ps1 start hidden every time you log in to Windows, and starts it now.
# Run once per PC (after cloning):   powershell -ExecutionPolicy Bypass -File install-autosync.ps1
# To turn it off:                    powershell -ExecutionPolicy Bypass -File install-autosync.ps1 -Remove

param([switch]$Remove)

$script = Join-Path $PSScriptRoot "autosync.ps1"
$lnk = Join-Path ([Environment]::GetFolderPath("Startup")) "11-september autosync.lnk"
$psArgs = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""

# stop any copy already running for this folder
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -like "*$script*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

if ($Remove) {
  if (Test-Path $lnk) { Remove-Item $lnk }
  "Auto-sync removed and stopped."
  return
}

$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($lnk)
$s.TargetPath = "powershell.exe"
$s.Arguments = $psArgs
$s.WorkingDirectory = $PSScriptRoot
$s.WindowStyle = 7
$s.Save()

Start-Process powershell.exe -ArgumentList $psArgs -WindowStyle Hidden
"Auto-sync installed and running. It will also start at every login. Log: $(Join-Path $PSScriptRoot 'autosync.log')"
