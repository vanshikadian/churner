#!/bin/bash
echo "=== ChurnShield Backend Starting ==="

echo "Seeding database (skips if already populated)..."
python /app/seed.py

# Train models for any vertical that doesn't have one yet
for vertical in b2b_saas entertainment lifestyle marketplace; do
    if [ ! -f "/app/ml/${vertical}_model.joblib" ]; then
        echo "Training ML model for ${vertical}..."
    fi
done

# Train all at once (fast — skips verticals with no users)
python /app/ml/train.py

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
