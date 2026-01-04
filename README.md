# WhatsApp Data Ingestion Backend

This is a high-performance FastAPI backend designed to ingest, validate, store, and analyze WhatsApp-like messages.

## 🚀 Features
* **Security**: HMAC SHA256 signature validation.
* **Idempotency**: Prevents duplicates using Database constraints.
* **Observability**: Structured JSON Logging & Prometheus Metrics.
* **Deployment**: Dockerized with multi-stage builds.

## 🛠️ Setup & Running
**Prerequisite:** Docker installed.

1.  **Build and Run:**
    ```bash
    docker compose up --build
    ```
2.  **Access Endpoints:**
    * Health: `http://localhost:8000/health/live`
    * Metrics: `http://localhost:8000/metrics`
    * Messages: `http://localhost:8000/messages`

## 🧪 Testing
A python script is included to simulate signed webhook requests.
```bash
python test_request.py