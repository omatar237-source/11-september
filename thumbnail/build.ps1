# Rebuilds thumbnail\thumbnail.html from template.html, embedding the presenter photo.
$d = $PSScriptRoot
$s = [IO.File]::ReadAllText("$d\template.html").Replace("__PHOTO__", "data:image/jpeg;base64," + [Convert]::ToBase64String([IO.File]::ReadAllBytes("$d\photo.jpg"))).Replace("__TOWERS__", "data:image/jpeg;base64," + [Convert]::ToBase64String([IO.File]::ReadAllBytes("$d\towers.jpg")))
[IO.File]::WriteAllText("$d\thumbnail.html", $s, (New-Object Text.UTF8Encoding($false)))
