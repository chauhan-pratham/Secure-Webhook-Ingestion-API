# --- STAGE 1: Builder ---
# CHANGE HERE: Use 3.10 so it understands "str | None"
FROM python:3.10-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# --- STAGE 2: Runner ---
# CHANGE HERE: Use 3.10 here as well
FROM python:3.10-slim

WORKDIR /app

COPY --from=builder /install /usr/local

COPY main.py .
COPY storage.py .
COPY schema.py .
COPY logging_utils.py .
COPY metrics.py .

RUN mkdir -p /data

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]