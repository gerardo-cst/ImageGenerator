$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m scripts.check_deploy_idle
if ($LASTEXITCODE -ne 0) { throw 'Deploy in uso: chiudere CST RenderAI prima di aggiornare' }
& "$PSScriptRoot/build.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Build fallita' }
# Mirror runtime only; never delete user data already stored in deploy/data.
New-Item -ItemType Directory -Force deploy | Out-Null
robocopy dist/CST_RenderAI deploy /E /R:2 /W:1 /NFL /NDL /NJH /NJS
if ($LASTEXITCODE -gt 7) { throw 'Copia deploy fallita' }
Copy-Item packaging/portable.ini deploy/portable.ini
Copy-Item packaging/LEGGIMI.txt deploy/LEGGIMI.txt
Copy-Item packaging/GUIDA_USO.txt deploy/GUIDA_USO.txt
Copy-Item packaging/Avvia.bat deploy/Avvia.bat
python -m scripts.bundle_codex
if ($LASTEXITCODE -ne 0) { throw 'Integrazione motore Codex fallita' }
New-Item -ItemType Directory -Force deploy/data | Out-Null
$global:LASTEXITCODE = 0
Write-Output 'Deploy pronto: deploy/CST_RenderAI.exe'
