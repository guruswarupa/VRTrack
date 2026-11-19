<#
.SYNOPSIS
  Builds the VRTrack Windows installer (VRTrack app + bundled OpenTrack).

.DESCRIPTION
  1. Downloads the pinned official OpenTrack setup and verifies its SHA-256 (installer\opentrack.json).
  2. Freezes the desktop app with PyInstaller.
  3. Compiles installer\vrtrack.iss with Inno Setup (ISCC).
  Output: installer\build\out\VRTrack-Setup-<version>.exe

  Needs: Python 3.10+ with `pip install -r pc/requirements.txt pyinstaller`, and Inno Setup 6.
#>
param(
  [string]$Iscc = "",
  [switch]$SkipExe
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$build = Join-Path $PSScriptRoot "build"
New-Item -ItemType Directory -Force $build | Out-Null

# ---- version
$version = (python -c "import sys; sys.path.insert(0, r'$root\pc'); import vrtrack; print(vrtrack.__version__)").Trim()
Write-Host "VRTrack version $version"

# ---- OpenTrack (pinned + verified)
$ot = Get-Content (Join-Path $PSScriptRoot "opentrack.json") | ConvertFrom-Json
$otFile = Join-Path $build "opentrack-setup.exe"
$need = $true
if (Test-Path $otFile) {
  $need = (Get-FileHash $otFile -Algorithm SHA256).Hash.ToLower() -ne $ot.sha256
}
if ($need) {
  Write-Host "Downloading OpenTrack $($ot.version)..."
  Invoke-WebRequest -Uri $ot.url -OutFile $otFile -UseBasicParsing
}
$actual = (Get-FileHash $otFile -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $ot.sha256) { throw "OpenTrack checksum mismatch: expected $($ot.sha256), got $actual" }
Write-Host "OpenTrack checksum OK"

# ---- freeze the app
if (-not $SkipExe) {
  Push-Location $PSScriptRoot
  python -m PyInstaller --noconfirm --clean --windowed --name VRTrack `
    --icon "$root\pc\vrtrack\assets\icon.ico" `
    --paths "$root\pc" `
    --add-data "$root\pc\vrtrack\assets;vrtrack\assets" `
    --distpath "$build\dist" --workpath "$build\work" --specpath "$build" `
    "$root\pc\packaging\run_vrtrack.py"
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
  Pop-Location
}

# ---- compile the installer
if (-not $Iscc) {
  $cands = @(
    (Get-Command iscc -ErrorAction SilentlyContinue).Source,
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
  ) | Where-Object { $_ -and (Test-Path $_) }
  if (-not $cands) { throw "Inno Setup (ISCC.exe) not found. Install Inno Setup 6 or pass -Iscc <path>." }
  $Iscc = $cands | Select-Object -First 1
}
Push-Location $PSScriptRoot
& $Iscc "/DAppVersion=$version" "/DOpenTrackVersion=$($ot.version)" "/DOpenTrackSetup=$otFile" "vrtrack.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
Pop-Location
Write-Host "Installer: $build\out\VRTrack-Setup-$version.exe"
