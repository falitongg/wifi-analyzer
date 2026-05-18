import os
from dotenv import load_dotenv

load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID")

TOPIC_BASE = "nsi/wifi-monitor"
TOPIC_TELEMETRY = f"{TOPIC_BASE}/telemetry"
TOPIC_INTERVAL = f"{TOPIC_BASE}/interval"
TOPIC_MANIPULATE = f"{TOPIC_BASE}/manipulate"
TOPIC_STATUS = f"{TOPIC_BASE}/status"

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in environment!")