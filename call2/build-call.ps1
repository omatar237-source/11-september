# Rebuilds call2\flight-11-sweeney-call.html from call2\template.html, embedding the photo and the call audio.
$d = $PSScriptRoot
$s = [IO.File]::ReadAllText("$d\template.html")
$s = $s.Replace("__PHOTO__", "data:image/jpeg;base64," + [Convert]::ToBase64String([IO.File]::ReadAllBytes("$d\photo.jpg")))
$s = $s.Replace("__AUDIO__", "data:audio/mp4;base64," + [Convert]::ToBase64String([IO.File]::ReadAllBytes("$d\call-audio.m4a")))
[IO.File]::WriteAllText("$d\flight-11-sweeney-call.html", $s, (New-Object Text.UTF8Encoding($false)))
