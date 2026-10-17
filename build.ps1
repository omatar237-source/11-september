$s = [IO.File]::ReadAllText("$PSScriptRoot\template.html")
$m = @{1='1.png';2='2.png';3='3.png';4='4.webp';5='5.png';6='6.webp'}
foreach ($k in $m.Keys) { $p = "$PSScriptRoot\images\$($m[$k])"; $mime = if ($p -like '*.webp') {'image/webp'} else {'image/png'}
  $s = $s.Replace("__IMG$($k)__", "data:$mime;base64," + [Convert]::ToBase64String([IO.File]::ReadAllBytes($p))) }
[IO.File]::WriteAllText("$PSScriptRoot\detective-board.html", $s, (New-Object Text.UTF8Encoding($false)))