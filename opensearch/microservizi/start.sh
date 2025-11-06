#!/bin/bash

# Script per avviare il microservizio MSSQL Upload

echo "========================================"
echo "🚀 Avvio Microservizio MSSQL Upload"
echo "========================================"

# Controlla se esiste virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creazione virtual environment..."
    python3 -m venv venv
fi

# Attiva virtual environment
echo "🔧 Attivazione virtual environment..."
source venv/bin/activate

# Installa/aggiorna dipendenze
echo "📥 Installazione dipendenze..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Controlla se esiste file .env
if [ ! -f ".env" ]; then
    echo "⚠️  File .env non trovato!"
    echo "📝 Copia .env.example in .env e configura le credenziali"
    cp .env.example .env
    echo "⚙️  File .env creato - configura le credenziali prima di procedere"
    exit 1
fi

# Carica variabili d'ambiente
export $(cat .env | grep -v '^#' | xargs)

echo ""
echo "✅ Setup completato!"
echo ""
echo "📡 Avvio API su porta ${API_PORT:-8000}..."
echo "📚 Documentazione disponibile su: http://localhost:${API_PORT:-8000}/docs"
echo ""
echo "Per fermare il server premi Ctrl+C"
echo ""

# Avvia server
python api.py
