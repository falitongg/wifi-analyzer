import network
import time
import json
from umqtt.simple import MQTTClient
import config
import indicators

class MQTTManager:
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.client = MQTTClient(
            client_id=config.MQTT_CLIENT_ID,
            port=config.MQTT_PORT,
            server=config.MQTT_BROKER,
            user=config.MQTT_USER,
            password=config.MQTT_PASSWORD,
            keepalive=60
        )
        self.connected = False
        self.failed_attempts = 0
        
        # Timers for non-blocking operations
        self.last_wifi_attempt = 0
        self.last_mqtt_attempt = 0

    def connect_wifi(self):
        """Non-blocking Wi-Fi connection handler."""
        self.wlan.active(True)
        
        if self.wlan.isconnected() and self.wlan.status() == 3:
            return True
            
        current_time = time.ticks_ms()
        
        # Initiate connection only once every 10 seconds to prevent spamming
        if time.ticks_diff(current_time, self.last_wifi_attempt) > 10000 or self.last_wifi_attempt == 0:
            print(f'[INFO] Connecting to Wi-Fi... status={self.wlan.status()}')
            self.wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
            self.last_wifi_attempt = current_time
            
        return False

    def connect_mqtt(self):
        """Non-blocking MQTT connection handler."""
        current_time = time.ticks_ms()
        
        # Try connecting to MQTT only once every 5 seconds
        if time.ticks_diff(current_time, self.last_mqtt_attempt) > 5000 or self.last_mqtt_attempt == 0:
            self.last_mqtt_attempt = current_time
            try:
                self.client.connect()
                print("[INFO] MQTT connected")
                self.connected = True
                self.failed_attempts = 0
                return True
            except Exception as e:
                self.connected = False
                print(f'[ERROR] Failed to establish an MQTT connection: {e}')
                self._handle_failure()
                
        return False

    def publish_data(self, data):
        """Non-blocking data publish."""
        if not data:
            return False

        # Check and handle network connections silently
        if not self.connect_wifi():
            return False

        if not self.connected:
            if not self.connect_mqtt():
                return False

        payload = json.dumps(data)

        # Execute a single attempt per call
        try:
            self.client.publish(config.MQTT_TOPIC, payload, qos=1)
            print("[INFO] Data sent successfully")
            self.failed_attempts = 0
            return True
        except OSError as e:
            self.connected = False
            print(f"[ERROR] MQTT publish failed: {e}")
            self._handle_failure()
            return False
        
    def ping(self):
        if seld.connected:
            try:
                self.client.ping()
                return True
            except OSError as e:
                self.connected = False
                print(f"[ERROR] MQTT ping failed: {e}")
                self._handle_failure()
        return False
            
    def _handle_failure(self):
        """Tracks failures and triggers error indicator after max retries."""
        self.failed_attempts += 1
        print(f"[WARNING] Attempt {self.failed_attempts}/3 failed")
        
        if self.failed_attempts >= 3:
            print("[ERROR] Max retries reached, triggering indicator")
            indicators.mqtt_error()
            self.failed_attempts = 0