import json
import hmac
import hashlib
import os
import time
import uuid
from dotenv import load_dotenv

from fastapi import FastAPI, Header, HTTPException, Request, Query, Response
from fastapi.responses import PlainTextResponse

# Custom modules
import storage
import logging_utils
import metrics
from schema import WhatsAppMessage  # Assuming you renamed models.py to schema.py

load_dotenv()

app = FastAPI()

# Configuration
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "default_secret_for_testing")

# Initialize DB on startup
storage.init_db()

# --- 1. SINGLE, COMBINED MIDDLEWARE ---
@app.middleware("http")
async def log_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # METRICS: Count every HTTP request
    metrics.inc("http_requests_total", {
        "path": request.url.path, 
        "status": str(response.status_code)
    })
    
    # LOGGING: Log everything EXCEPT /webhook (which we log manually for more detail)
    if request.url.path != "/webhook":
        logging_utils.log_request(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency=process_time
        )
        
    return response


@app.post("/webhook")
async def ingest_whatsapp_message(request: Request, x_signature: str = Header(None, alias="X-Signature")):
    # Start timer for manual logging
    start_time = time.time()
    request_id = str(uuid.uuid4())

    # 1. Security Logic
    body_bytes = await request.body()

    if not x_signature:
        # Metric for failure
        metrics.inc("webhook_requests_total", {"result": "missing_signature"}) 
        raise HTTPException(401, "No signature")

    expected_signature = hmac.new(
        key=WEBHOOK_SECRET.encode(), 
        msg=body_bytes, 
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(x_signature, expected_signature):
        # Metric for failure
        metrics.inc("webhook_requests_total", {"result": "invalid_signature"})
        # Log the failure
        logging_utils.log_request(
            request_id=request_id, method="POST", path="/webhook", 
            status=401, latency=time.time() - start_time,
            result="invalid_signature"
        )
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # 2. Parsing Logic
    try:
        data = json.loads(body_bytes)
        msg = WhatsAppMessage(**data)
    except Exception:
        metrics.inc("webhook_requests_total", {"result": "validation_error"})
        raise HTTPException(422, "Invalid JSON")
    
    # 3. Storage Logic (Capture the result!)
    # storage.insert_message returns True if new, False if duplicate
    was_inserted = storage.insert_message(msg.message_id, msg.from_, msg.to, msg.ts, msg.text)

    # Determine status for Logs & Metrics
    status_result = "created" if was_inserted else "duplicate"
    is_dup = not was_inserted

    # Update Metrics
    metrics.inc("webhook_requests_total", {"result": status_result})

    # Log the specific requirement 
    logging_utils.log_request(
        request_id=request_id,
        method="POST",
        path="/webhook",
        status=200,
        latency=time.time() - start_time,
        message_id=msg.message_id,
        dup=is_dup,
        result=status_result
    )

    return {"status": "ok"}


@app.get("/messages")
def list_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_: str | None = Query(None, alias="from"),
    since: str | None = None,
    q: str | None = None
):
    # Note: Ensure this matches the function name in storage.py (get_messages vs get_message)
    data, total = storage.get_messages(
        limit=limit,
        offset=offset,
        from_msisdn=from_,
        since=since,
        text_search=q
    )

    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/stats")
def get_analytics():
    stats_data = storage.get_stats()
    return stats_data   


@app.get("/health/live")
def health_live():
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready(response: Response):
    db_is_ok = storage.check_db()
    secret_is_set = WEBHOOK_SECRET and WEBHOOK_SECRET != "default_secret_for_testing"
    
    if db_is_ok and secret_is_set:
        return {"status": "ready"}
    else:
        response.status_code = 503
        return {
            "status": "not ready", 
            "db": "up" if db_is_ok else "down",
            "secret": "set" if secret_is_set else "missing"
        }


@app.get("/metrics")
def get_metrics():
    return PlainTextResponse(metrics.generate_text())