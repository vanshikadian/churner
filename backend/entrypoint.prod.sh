#!/bin/bash
set -e

echo "=== ChurnShield Backend Starting (production) ==="

echo "Seeding database (skips if already populated)..."
python /app/seed.py

echo "Training ML models..."
python /app/ml/train.py

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
