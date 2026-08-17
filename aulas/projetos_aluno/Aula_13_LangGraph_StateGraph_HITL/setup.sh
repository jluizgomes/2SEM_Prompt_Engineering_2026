#!/bin/bash
# ============================================================
# Setup — Projeto de Aula (FIAP Prompt Engineering & AI)
# Configura o ambiente virtual e instala as dependências.
#
# Uso:
#   chmod +x setup.sh
#   ./setup.sh
#
# Após executar, ative o ambiente:
#   source .venv/bin/activate
# ============================================================

set -e  # Encerra se qualquer comando falhar

echo "🔧 Configurando ambiente virtual..."

# Cria o venv
python3 -m venv .venv

# Ativa o venv
source .venv/bin/activate

# Atualiza pip
pip install --upgrade pip --quiet

# Instala as dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Copia .env.example → .env (se .env ainda não existir)
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo "📋 Arquivo .env criado a partir do .env.example"
    echo "   ⚠️  Edite o .env e preencha OLLAMA_API_KEY antes de rodar."
fi

echo ""
echo "✅ Ambiente configurado com sucesso!"
echo ""
echo "Para ativar o ambiente virtual:"
echo "  source .venv/bin/activate"
echo ""
echo "Para rodar o projeto:"
echo "  python main.py"
