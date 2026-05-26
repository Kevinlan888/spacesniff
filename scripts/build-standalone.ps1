$ErrorActionPreference = 'Stop'

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$Python = Join-Path $RootDir '.venv\Scripts\python.exe'
$Pip = Join-Path $RootDir '.venv\Scripts\pip.exe'
$PyInstaller = Join-Path $RootDir '.venv\Scripts\pyinstaller.exe'

if (-not (Test-Path $Python)) {
    Write-Error 'missing virtual environment at .venv'
}

& $Python -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error 'pyinstaller is not installed in .venv; run: .venv\Scripts\pip install pyinstaller'
}

if (Test-Path build) {
    Remove-Item build -Recurse -Force
}
if (Test-Path dist) {
    Remove-Item dist -Recurse -Force
}

& $PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name spacesniff `
  --collect-all textual `
  --collect-all rich `
  spacesniff/__main__.py

Write-Host ''
Write-Host "Standalone binary created at: $RootDir\dist\spacesniff.exe"
