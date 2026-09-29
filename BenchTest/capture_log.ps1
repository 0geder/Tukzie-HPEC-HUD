param([int]$Seconds = 150, [int]$ShakeAt = 50, [int]$ShakeFor = 20, [int]$WaitMax = 1800, [string]$Out)

function Test-PortFree {
  $p = New-Object System.IO.Ports.SerialPort COM10,115200
  try { $p.Open(); $p.Close(); return $true } catch { return $false }
}

# Wait (up to 5 min) for whoever holds COM10 to release it.
$waitStart = Get-Date
while (-not (Test-PortFree)) {
  if (((Get-Date) - $waitStart).TotalSeconds -gt $WaitMax) { "gave up: COM10 still in use after $WaitMax s"; exit 1 }
  Start-Sleep -Milliseconds 500
}

# Reset the board so the log starts from power-up (boot self-tests included).
$esptool = "$env:USERPROFILE\.platformio\packages\tool-esptoolpy\esptool.py"
$py = "$env:USERPROFILE\.platformio\penv\Scripts\python.exe"
& $py $esptool --chip esp32s3 --port COM10 --after hard_reset read_mac *> $null

$port = New-Object System.IO.Ports.SerialPort COM10,115200,None,8,one
$port.ReadTimeout = 1000
$opened = $false
for ($i = 0; $i -lt 100 -and -not $opened; $i++) {
  try { $port.Open(); $opened = $true } catch { Start-Sleep -Milliseconds 100 }
}
if (-not $opened) { "could not reopen COM10 after reset"; exit 1 }

$w = New-Object System.IO.StreamWriter($Out, $false, (New-Object System.Text.UTF8Encoding($false)))
$w.WriteLine("# SW7 bench capture, ESP32-S3 native USB (COM10), 115200 baud")
$w.WriteLine("# started " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + ", duration " + $Seconds + " s, captured from power-up")
$w.WriteLine("# protocol: board still, shaken by hand from ~" + $ShakeAt + " s to ~" + ($ShakeAt + $ShakeFor) + " s, then still")
[console]::beep(880, 300)

$n = 0; $cued1 = $false; $cued2 = $false
try {
  $start = Get-Date
  while (((Get-Date) - $start).TotalSeconds -lt $Seconds) {
    $el = ((Get-Date) - $start).TotalSeconds
    if (-not $cued1 -and $el -ge $ShakeAt) { $cued1 = $true; [console]::beep(1200, 200); [console]::beep(1200, 200) }
    if (-not $cued2 -and $el -ge ($ShakeAt + $ShakeFor)) { $cued2 = $true; [console]::beep(600, 200); [console]::beep(600, 200); [console]::beep(600, 200) }
    try {
      $line = $port.ReadLine().TrimEnd()
      $el = ((Get-Date) - $start).TotalSeconds
      $w.WriteLine(("[{0,7:F2}s] {1}" -f $el, $line)); $n++
    } catch [System.TimeoutException] { }
  }
} finally { if ($port.IsOpen) { $port.Close() }; $w.Close() }
[console]::beep(880, 600)
"captured $n lines to $Out"
