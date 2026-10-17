$l = New-Object Net.HttpListener; $l.Prefixes.Add("http://localhost:8765/"); $l.Start()
while ($l.IsListening) { $c = $l.GetContext(); $p = Join-Path $PSScriptRoot ($c.Request.Url.AbsolutePath.TrimStart('/'))
  if (Test-Path $p -PathType Leaf) { $b = [IO.File]::ReadAllBytes($p); $c.Response.ContentType = if ($p -like '*.html') {'text/html; charset=utf-8'} else {'application/octet-stream'}; $c.Response.OutputStream.Write($b,0,$b.Length) } else { $c.Response.StatusCode = 404 }
  $c.Response.Close() }