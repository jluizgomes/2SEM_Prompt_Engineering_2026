# ============================================================
# Setup — Projeto de Aula (FIAP Prompt Engineering & AI)
# Configura o ambiente virtual, instala as dependências Python
# E instala/compila o frontend (React) da interface web.
#
# Uso (PowerShell):
#   .\setup.ps1
#
# Depois é só abrir a interface web com:
#   .\rodar.ps1
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host " Configurando ambiente virtual (.venv)..." -ForegroundColor Cyan
python -m venv .venv

& .\.venv\Scripts\Activate.ps1

Write-Host " Atualizando pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip --quiet

Write-Host " Instalando dependências Python..." -ForegroundColor Cyan
pip install -r requirements.txt

# Copia .env.example -> .env (se .env ainda nao existir)
if (-not (Test-Path .env) -and (Test-Path .env.example)) {
    Copy-Item .env.example .env
    Write-Host " Arquivo .env criado a partir do .env.example" -ForegroundColor Yellow
    Write-Host "    Edite o .env e preencha OLLAMA_API_KEY antes de rodar." -ForegroundColor Yellow
}

# Frontend (React) — instala as libs e compila o dist
if (Test-Path frontend) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host " Instalando dependências do frontend (npm install)..." -ForegroundColor Cyan
        Push-Location frontend
        $oldEAP = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        npm install --no-fund --no-audit | Out-Null
        npm run build | Out-Null
        $ErrorActionPreference = $oldEAP
        Pop-Location
    } else {
        Write-Host " npm nao encontrado - o frontend ja vem compilado em frontend/dist." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host " Ambiente configurado com sucesso!" -ForegroundColor Green
Write-Host ""
Write-Host "Para abrir a interface web (React + FastAPI):"
Write-Host "  .\rodar.ps1"
Write-Host ""
Write-Host "Para rodar pelo terminal (CLI):"
Write-Host "  .\.venv\Scripts\Activate.ps1 ; python main.py"
