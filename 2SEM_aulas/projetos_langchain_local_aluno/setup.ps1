# ============================================================
# Setup — Projeto de Aula (FIAP Prompt Engineering & AI)
# Configura o ambiente virtual e instala as dependências.
#
# Uso (PowerShell):
#   .\setup.ps1
#
# Após executar, ative o ambiente:
#   .\.venv\Scripts\Activate.ps1
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host " Configurando ambiente virtual..." -ForegroundColor Cyan

# Cria o venv
python -m venv .venv

# Ativa o venv
& .\.venv\Scripts\Activate.ps1

# Atualiza pip
python -m pip install --upgrade pip --quiet

# Instala as dependencias
Write-Host " Instalando dependencias..." -ForegroundColor Cyan
pip install -r requirements.txt

# Copia .env.example -> .env (se .env ainda nao existir)
if (-not (Test-Path .env) -and (Test-Path .env.example)) {
    Copy-Item .env.example .env
    Write-Host " Arquivo .env criado a partir do .env.example" -ForegroundColor Yellow
    Write-Host "    Edite o .env e preencha OLLAMA_API_KEY antes de rodar." -ForegroundColor Yellow
}

Write-Host ""
Write-Host " Ambiente configurado com sucesso!" -ForegroundColor Green
Write-Host ""
Write-Host "Para ativar o ambiente virtual:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Para rodar o projeto:"
Write-Host "  python main.py"
