import json
import queue
from datetime import datetime
from database import save_scan

sse_queue: queue.Queue = queue.Queue(maxsize=50)

def insert_telemetry_from_mqtt(topic: str, raw_data: str):

    try:
        data = json.loads(raw_data)
        
        ts = data.get("timestamp") or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        networks = data.get("networks", [])

        save_scan(ts, networks)

        event = {"type": "scan", "timestamp": ts, "networks": networks}
        try:
            sse_queue.put_nowait(event)
        except queue.Full:
            sse_queue.get_nowait()  # Drop the oldest event
            sse_queue.put_nowait(event)
            
        print(f"[Service] Processed telemetry: {len(networks)} networks")
        
    except json.JSONDecodeError:
        print("[Service] Invalid JSON data received.")
    except Exception as e:
        print(f"[Service] Failed to process telemetry: {e}")

def get_sse_queue() -> queue.Queue:
    """Return the queue for Flask endpoints."""
    return sse_queue