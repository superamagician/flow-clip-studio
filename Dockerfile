# Production image for Render/Railway: Python + ffmpeg + a Thai-capable font
# (needed for the watermark drawtext filter in app.py's apply_watermark()).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        fonts-tlwg-garuda \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

# Runs the schema migration (idempotent CREATE TABLE IF NOT EXISTS) then starts gunicorn.
CMD ["sh", "-c", "python -c 'import db; db.init_db()' && gunicorn -b 0.0.0.0:$PORT -w 2 --timeout 120 app:app"]
