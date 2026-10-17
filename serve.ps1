# Local preview server for detective-board.html (http://localhost:8765/detective-board.html).
# GET serves files from this folder; POST /save/<name> writes the exported video into output\<name>.
$l = New-Object Net.HttpListener; $l.Prefixes.Add("http://localhost:8765/"); $l.Start()
while ($l.IsListening) { $c = $l.GetContext(); $path = [Uri]::UnescapeDataString($c.Request.Url.AbsolutePath)
  if ($c.Request.HttpMethod -eq 'POST' -and $path -match '^/save/([\w.\-]+)$') {
    $dir = Join-Path $PSScriptRoot 'output'; New-Item -ItemType Directory -Force $dir | Out-Null
    $fs = [IO.File]::Create((Join-Path $dir $Matches[1])); $c.Request.InputStream.CopyTo($fs); $fs.Close()
    $c.Response.StatusCode = 200
  } else {
    $p = Join-Path $PSScriptRoot $path.TrimStart('/')
    if (Test-Path $p -PathType Leaf) { $b = [IO.File]::ReadAllBytes($p); $c.Response.ContentType = if ($p -like '*.html') {'text/html; charset=utf-8'} else {'application/octet-stream'}; $c.Response.OutputStream.Write($b,0,$b.Length) } else { $c.Response.StatusCode = 404 }
  }
  $c.Response.Close() }
