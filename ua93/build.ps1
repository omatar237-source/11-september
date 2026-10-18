# Rebuilds ua93\flight-93.html from template.html, embedding the map outlines and the voice-over.
$d = $PSScriptRoot
$s = [IO.File]::ReadAllText("$d\template.html").Replace("__MAP__", [IO.File]::ReadAllText("$d\usmap.json"))
$s = $s.Replace("__VO__", "data:audio/mp4;base64," + [Convert]::ToBase64String([IO.File]::ReadAllBytes("$d\voiceover.m4a")))
[IO.File]::WriteAllText("$d\flight-93.html", $s, (New-Object Text.UTF8Encoding($false)))
