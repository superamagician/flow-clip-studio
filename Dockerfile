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
# gthread + threads=4: this app's request handling is almost entirely I/O wait
# (calling useapi.net, Supabase Storage, Postgres) rather than CPU work, so plain
# sync workers (the old config) meant a single slow/stuck outbound call occupied
# a whole worker process - with only 2 of them, a few concurrent status polls
# hitting a slow moment on useapi.net was enough to make the entire site
# unresponsive for every user. Threads let each worker process serve several
# requests concurrently while most of them are just waiting on a network call.
CMD ["sh", "-c", "python -c 'import db; db.init_db()' && gunicorn -b 0.0.0.0:$PORT -w 2 --worker-class gthread --threads 4 --timeout 240 app:app"]
