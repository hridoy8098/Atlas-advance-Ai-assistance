# Atlas 7.0 — Hugging Face Spaces (Docker) deployment
# Build the React UI first, then serve it from FastAPI on port 7860.

FROM node:20-alpine AS frontend-build
WORKDIR /web
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ATLAS_VOICE_AUTOSTART=0 \
    PORT=7860

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-hf.txt ./
RUN pip install --no-cache-dir -r requirements-hf.txt

COPY . .
COPY --from=frontend-build /web/dist ./frontend/dist

EXPOSE 7860

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
