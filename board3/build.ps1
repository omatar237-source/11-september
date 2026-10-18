$s = [IO.File]::ReadAllText("$PSScriptRoot\template.html")
$m = @{1='1.png';2='2.png';3='3.png';4='4.png';5='5.png';6='6.webp'}
foreach ($k in $m.Keys) { $p = "$PSScriptRoot\images\$($m[$k])"; $mime = if ($p -like '*.webp') {'image/webp'} else {'image/png'}
  $s = $s.Replace("__IMG$($k)__", "data:$mime;base64," + [Convert]::ToBase64String([IO.File]::ReadAllBytes($p))) }
# voice-over (optional): any audio/video file at audio\voiceover.mp4 — only its sound is used
$vo = "$PSScriptRoot\audio-voiceover.m4a"
$voData = if (Test-Path $vo) { "data:video/mp4;base64," + [Convert]::ToBase64String([IO.File]::ReadAllBytes($vo)) } else { "" }
$s = $s.Replace("__VO__", $voData)
[IO.File]::WriteAllText("$PSScriptRoot\detective-board.html", $s, (New-Object Text.UTF8Encoding($false)))