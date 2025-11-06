#!/bin/bash

# DocSearch - Run Script

echo "🚀 Starting DocSearch..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "✏️  Please edit .env file with your configuration"
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if OpenSearch is running
echo ""
echo "🔍 Checking OpenSearch connection..."
python3 << EOF
from opensearch_manager import OpenSearchManager
try:
    manager = OpenSearchManager()
    print("✅ OpenSearch is running!")
except Exception as e:
    print(f"❌ OpenSearch connection failed: {e}")
    print("")
    print("💡 To start OpenSearch with Docker:")
    print("   docker-compose up -d opensearch")
    exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi

# Run Flask app
echo ""
echo "🌐 Starting Flask application..."
echo "📍 URL: http://localhost:${PORT:-5000}"
echo ""

python3 app.py
