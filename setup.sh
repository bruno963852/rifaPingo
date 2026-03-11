#!/bin/bash
# Script para instalar dependências e configurar o projeto

echo "Instalando dependências..."
pip3 install -r requirements.txt

echo "Criando arquivo .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Arquivo .env criado. Edite-o com suas credenciais de email!"
else
    echo "✓ Arquivo .env já existe"
fi

echo ""
echo "Instalação concluída!"
echo "Para iniciar a aplicação, execute: python3 app.py"
echo "Acesse: http://localhost:5000"
