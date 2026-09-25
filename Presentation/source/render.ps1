param([string]$Pptx, [string]$OutDir, [int]$Width = 1600)
# Render every slide of a .pptx to PNG using PowerPoint itself, for visual QA.
New-Item -ItemType Directory -Force $OutDir | Out-Null
Get-ChildItem $OutDir -Filter "slide-*.png" | Remove-Item -Force
$pp = New-Object -ComObject PowerPoint.Application
try {
  $deck = $pp.Presentations.Open((Resolve-Path $Pptx).Path, $true, $false, $false)  # read-only, no window
  $ratio = $deck.PageSetup.SlideHeight / $deck.PageSetup.SlideWidth
  $h = [int]($Width * $ratio)
  $i = 0
  foreach ($sl in $deck.Slides) {
    $i++
    $sl.Export((Join-Path $OutDir ("slide-{0:D2}.png" -f $i)), "PNG", $Width, $h)
  }
  $deck.Close()
  "rendered $i slide(s) at ${Width}x$h to $OutDir"
} finally { $pp.Quit(); [System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) | Out-Null }
