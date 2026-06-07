# ═══════════════════════════════════════════════════════════════════════
# Dockerfile — FastAPI Backend (Railway-compatible)
# Build dari ROOT context: docker build -t pdbl-backend -f backend/Dockerfile .
# ═══════════════════════════════════════════════════════════════════════

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cache layer)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy model files dari root ke /app/models/
RUN mkdir -p /app/models
COPY model_klasifikasi_loan.pkl /app/models/
COPY model_regresi_tuned_loan.pkl /app/models/
COPY threshold_tuned.pkl /app/models/

# Railway sets PORT env var automatically
ENV PORT=8000

EXPOSE ${PORT}

# Gunakan shell form agar $PORT ter-expand saat runtime
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
