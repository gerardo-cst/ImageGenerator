$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m scripts.make_icon
if ($LASTEXITCODE -ne 0) { throw 'Creazione icona fallita' }
python -m PyInstaller --noconfirm --clean --windowed --onedir --name CST_RenderAI --icon assets/app.ico --add-data 'assets;assets' run.py
if ($LASTEXITCODE -ne 0) { throw 'Build PyInstaller fallita' }
Copy-Item README.md dist/CST_RenderAI/README.md
Copy-Item TASKS.md dist/CST_RenderAI/TASKS.md
Copy-Item -Recurse -Force examples dist/CST_RenderAI/examples
Copy-Item -Recurse -Force docs dist/CST_RenderAI/docs
