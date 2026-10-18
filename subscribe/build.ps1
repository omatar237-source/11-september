# Rebuilds subscribe\subscribe.html from template.html, embedding the round avatar photo.
$d = $PSScriptRoot
$s = [IO.File]::ReadAllText("$d\template.html").Replace("__AVATAR__", "data:image/jpeg;base64," + [Convert]::ToBase64String([IO.File]::ReadAllBytes("$d\avatar.jpg")))
[IO.File]::WriteAllText("$d\subscribe.html", $s, (New-Object Text.UTF8Encoding($false)))
