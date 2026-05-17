import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MQTT_CLIENT_ID,
    TOPIC_TELEMETRY, TOPIC_INTERVAL, TOPIC_MANIPULATE, TOPIC_STATUS
)
from services import insert_telemetry_from_mqtt

device_status = "UNKNOWN"
mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)

def get_device_status():
    return device_status

def on_connect(client, userdata, flags, rc):
    client.subscribe(TOPIC_TELEMETRY)
    client.subscribe(TOPIC_STATUS)
    print("[MQTT] Connected, subscribed")

def on_message(client, userdata, msg):
    global device_status

    if msg.topic == TOPIC_STATUS:
        device_status = msg.payload.decode().strip()
        return

    if msg.topic == TOPIC_TELEMETRY:
        insert_telemetry_from_mqtt(msg.topic,msg.payload.decode("utf-8", errors="replace"))

def start_mqtt():
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.loop_start()