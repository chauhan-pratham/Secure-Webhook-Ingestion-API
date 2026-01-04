import json
import logging
import sys
from datetime import datetime, timezone

# [Requirement] Logs should be emitted to stdout (standard output)
# This is crucial for Docker containers so logs can be collected by AWS/Datadog.
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

def log_request(request_id, method, path, status, latency, **extras):
    """
    Emits a structured JSON log line. 
    Structured logs are machine-readable (easier to search than text logs).
    """
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "request_id": request_id,
        "method": method,
        "path": path,
        "status": status,
        "latency_ms": round(latency * 1000, 2) # Convert seconds to ms
    }
    # [Requirement] Merge extra fields (like message_id, result, dup)
    # This allows us to search logs like: 'result="duplicate"'
    log_entry.update(extras)
    
    # Print as a single JSON line
    print(json.dumps(log_entry), flush=True)