# ── builder ──────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

# Install wheels into an isolated prefix so the final stage just copies them.
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── runtime ──────────────────────────────────────────────────────────────────
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.13/site-packages"

WORKDIR /app

# Non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy installed packages from builder
COPY --from=builder /install /install

# Copy application source
COPY alembic.ini .
COPY migrations/ migrations/
COPY app/ app/

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

# Run migrations then start the server.
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000
