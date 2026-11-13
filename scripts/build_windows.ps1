$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
py -3.12 -m venv .build-venv
$py = Join-Path (Get-Location) '.build-venv\Scripts\python.exe'
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
if (-not (Test-Path 'vendor\nanovna-saver')) {
    New-Item -ItemType Directory -Force vendor | Out-Null
    git clone --depth 1 --branch v0.7.3 https://github.com/NanoVNA-Saver/nanovna-saver.git vendor/nanovna-saver
}
& $py -m pip install -e .\vendor\nanovna-saver
Push-Location vendor\nanovna-saver
$env:PYTHONPATH='src'
& $py -m tools.ui_compile
Pop-Location
& $py -c "import intvna; from intvna import IntVNA; print('IntVNA measurement module import OK')"
& $py -m PyInstaller --noconfirm --clean --onedir --windowed --name IntVNA `
  --paths "$PWD\src" --paths "$PWD\vendor\nanovna-saver\src" `
  --collect-all NanoVNASaver --collect-submodules PySide6 `
  --copy-metadata nanovnasaver src\intvna_app.py
New-Item -ItemType Directory -Force releases | Out-Null
Compress-Archive -Path 'dist\IntVNA' -DestinationPath 'releases\IntVNA-Windows-x64-beta.zip' -Force
Write-Host 'Created releases\IntVNA-Windows-x64-beta.zip'
