# Simple in-memory storage for metrics
# We store counters in a Python dict because the PDF forbids external DBs like Redis.
_counters = {}

def inc(name, labels):
    """
    Increments a counter. 
    Example: name="http_requests_total", labels={"status": "200"}
    """
    # Convert dict to Prometheus label string: 'status="200",path="/webhook"'
    # This specific format is required by Prometheus scrapers.
    label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
    key = f"{name}{{{label_str}}}"
    
    if key not in _counters:
        _counters[key] = 0
    _counters[key] += 1

def generate_text():
    """Returns the metrics in Prometheus text format."""
    lines = []
    for key, value in _counters.items():
        lines.append(f"{key} {value}")
    return "\n".join(lines)