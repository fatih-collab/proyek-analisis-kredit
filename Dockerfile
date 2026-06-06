# ═══════════════════════════════════════════════════════════
# Dockerfile — Python Backend (FastAPI)
# ═══════════════════════════════════════════════════════════

FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code and model files
COPY backend/ ./backend/
COPY *.pkl ./

ENV PYTHONUNBUFFERED=1

CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
