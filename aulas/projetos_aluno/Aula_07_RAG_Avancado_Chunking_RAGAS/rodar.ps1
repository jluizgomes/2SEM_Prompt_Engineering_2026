# =============================================================================
# rodar.ps1 — Roda ESTE exercicio (pasta autossuficiente).
#
# Prepara o ambiente (cria .venv, instala dependencias, compila o frontend se
# faltar) e sobe o servidor em PRIMEIRO PLANO. Ctrl+C encerra.
#
# Uso:  .\rodar.ps1 [porta]
# =============================================================================
param([int]$Porta = 8007)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[..] preparando ambiente local..."
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "[..] criando .venv..."
  python -m venv .venv
}
& ".venv\Scripts\python.exe" -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('fastapi') else 1)"
if ($LASTEXITCODE -ne 0) {
  Write-Host "[..] instalando dependencias (primeira vez)..."
  & ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
  if ($LASTEXITCODE -ne 0) { Write-Host "[!!] falha no pip install"; exit 1 }
}
if (-not (Test-Path "frontend\dist\index.html")) {
  Write-Host "[..] compilando frontend (primeira vez)..."
  Push-Location frontend
  npm install --no-fund --no-audit | Out-Null
  if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "[!!] falha no npm install"; exit 1 }
  npm run build | Out-Null
  if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "[!!] falha no build"; exit 1 }
  Pop-Location
}

Write-Host ""
Write-Host "[ok] servidor em: http://127.0.0.1:$Porta"
Write-Host "[..] Ctrl+C para encerrar."
Write-Host ""
& ".venv\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port $Porta
