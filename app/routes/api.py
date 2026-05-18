import json
import queue

from flask import Blueprint, render_template, jsonify, request, Response

from database import get_scans, get_latest_scan, get_scan_by_id
from mqtt.mqtt_handler import mqtt_client, get_device_status
from services import get_sse_queue
from config import TOPIC_MANIPULATE, TOPIC_INTERVAL

api_bp = Blueprint("api", __name__)

@api_bp.route("/health")
def health():
    return "ok", 200

@api_bp.route("/")
def index():
    return render_template("index.html")


@api_bp.route("/scanner/toggle", methods=["POST"])
def toggle_scanner():
    body = request.get_json(force=True)
    state = body.get("state", "on").lower()
    if state not in ("on", "off", "shutdown"):
        return jsonify(error="state must be 'on', 'off' or 'shutdown'"), 400

    mqtt_client.publish(TOPIC_MANIPULATE, state)
    return jsonify(ok=True, state=state)


@api_bp.route("/scanner/interval", methods=["POST"])
def set_interval():
    body = request.get_json(force=True)
    try:
        interval = int(body.get("interval", 10))
    except (ValueError, TypeError):
        return jsonify(error="interval must be an integer"), 400

    if not (5 <= interval <= 150):
        return jsonify(error="interval must be 5–150 s"), 400

    mqtt_client.publish(TOPIC_INTERVAL, str(interval))
    return jsonify(ok=True, interval=interval)


@api_bp.route("/scanner/status")
def scanner_status():
    return jsonify(
        mqtt_connected=mqtt_client.is_connected(),
        device_status=get_device_status()
    )


@api_bp.route("/scans")
def list_scans():
    from_ts = request.args.get("from", "")
    to_ts = request.args.get("to", "")
    try:
        limit = min(int(request.args.get("limit", 100)), 5000)
    except ValueError:
        limit = 100

    return jsonify(get_scans(from_ts=from_ts, to_ts=to_ts, limit=limit))


@api_bp.route("/scans/latest")
def latest_scan():
    scan = get_latest_scan()
    if not scan:
        return jsonify(error="No scans found"), 404
    return jsonify(scan)


@api_bp.route("/scans/<int:scan_id>")
def get_scan(scan_id):
    scan = get_scan_by_id(scan_id)
    if not scan:
        return jsonify(error="Scan not found"), 404
    return jsonify(scan)


@api_bp.route("/events")
def sse_stream():
    sse_queue = get_sse_queue()

    def generate():
        yield "data: {\"type\":\"connected\"}\n\n"
        while True:
            try:
                event = sse_queue.get(timeout=20)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )