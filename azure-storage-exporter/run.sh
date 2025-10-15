#!/bin/bash
# Quick runner script for Azure Storage Exporter

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [[ ! -d "venv" ]]; then
    echo "Error: Virtual environment not found. Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source venv/bin/activate

# Load environment variables from .env if exists
if [[ -f ".env" ]]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Run the exporter
echo "Starting Azure Storage Exporter..."
python azure_storage_exporter.py "$@"
