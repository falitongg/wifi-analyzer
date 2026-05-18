"""
MQTT client manager for the Pico W Wi-Fi monitor.

Wi-Fi status checks and connection attempts are delegated to
WLANManager so that this module never creates its own WLAN object.
"""
import socket
import time
import json
from umqtt.simple import MQTTClient
import config
import indicators
import machine

class MQTTManager:
    """
    Manages an MQTT session over the shared Wi-Fi interface.

    Parameters
    ----------
    wlan_manager : WLANManager
        Injected by main.py; used for Wi-Fi status queries and
        queuing connection attempts.
    """

    # Minimum time between consecutive broker connection attempts (ms)
    _MQTT_COOLDOWN_MS = 15_000

    def __init__(self, wlan_manager):
        self._wm = wlan_manager

        self.client = MQTTClient(
            client_id=config.MQTT_CLIENT_ID,
            server=config.MQTT_BROKER,
            port=config.MQTT_PORT,
            user=config.MQTT_USER,
            password=config.MQTT_PASSWORD,
            keepalive=60,
        )
        
        self.client.set_last_will(
            config.MQTT_TOPIC_STATUS,
            b"offline",
            retain=True,
            qos=1
        )
        self.client.set_callback(self._on_message)

        self.connected       = False
        self.scanning_enabled = True
        self.scan_interval   = config.SCAN_INTERVAL  # ms; may be updated via MQTT

        self._last_mqtt_attempt = 0  # ticks_ms of last broker connect call
    
    def _is_broker_reachable(self):
        """
        Attempts a quick TCP connection to the broker.
        Prevents blocking the main loop if the broker is down.
        """
        try:
            addr = socket.getaddrinfo(config.MQTT_BROKER, config.MQTT_PORT)[0][-1]
            s = socket.socket()
            s.settimeout(1.0)
            s.connect(addr)
            s.close()
            return True
        except OSError as e:
            print(f"[DEBUG] Socket probe failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Incoming MQTT message handler
    # ------------------------------------------------------------------

    def _on_message(self, topic, msg):
        """
        Dispatch incoming MQTT messages to the appropriate handler.

        topic and msg arrive as bytes from umqtt; msg is decoded here.
        topic is compared directly as bytes against the config constants
        (which are also defined as b'...' byte literals).
        """
        decoded = msg.decode().strip()
        print(f"[MQTT] {topic} -> {decoded}")

        if topic == config.MQTT_TOPIC_MANIPULATE:
            cmd = decoded.lower()
            if cmd == "on" and not self.scanning_enabled:
                self.scanning_enabled = True
                print("[INFO] Scanning enabled")
            elif cmd == "off" and self.scanning_enabled:
                self.scanning_enabled = False
                print("[INFO] Scanning disabled")
            elif cmd == "shutdown":
                print("[INFO] Shutdown requested via MQTT — restarting in 1 s")
                try:
                    self.client.publish(
                        config.MQTT_TOPIC_STATUS, b"offline", retain=True, qos=1
                    )
                except Exception:
                    pass
                time.sleep(1)
                machine.reset()
                
        elif topic == config.MQTT_TOPIC_INTERVAL:
            try:
                secs = int(decoded)
                if 5 <= secs <= 150:
                    self.scan_interval = secs * 1000
                    print(f"[INFO] Scan interval set to {secs}s")
            except ValueError:
                pass  # ignore malformed payloads

    # ------------------------------------------------------------------
    # Wi-Fi helpers (delegated to WLANManager)
    # ------------------------------------------------------------------

    def is_wifi_up(self):
        """Return True when the shared WLAN interface has an IP address."""
        return self._wm.is_connected()

    def connect_wifi(self):
        """Ask WLANManager to queue a Wi-Fi connection attempt."""
        self._wm.request_connect()

    # ------------------------------------------------------------------
    # MQTT lifecycle
    # ------------------------------------------------------------------

    def connect_mqtt(self):
        """
        Connect to the broker and subscribe to control topics.

        Enforces _MQTT_COOLDOWN_MS between retries to avoid hammering
        the broker on repeated failures.

        Returns
        -------
        bool
            True on success, False on failure or during cooldown.
        """
        now = time.ticks_ms()
        if self._last_mqtt_attempt != 0 and \
                time.ticks_diff(now, self._last_mqtt_attempt) < self._MQTT_COOLDOWN_MS:
            return False

        self._last_mqtt_attempt = now
        
        print("[INFO] Probing MQTT broker...")
        if not self._is_broker_reachable():
            self.connected = False
            print("[ERROR] Broker unreachable, skipping connect")
            return False
        
        try:
            self.client.connect()
            # Subscribe to both control topics after a fresh connection
            self.client.subscribe(config.MQTT_TOPIC_INTERVAL)
            self.client.subscribe(config.MQTT_TOPIC_MANIPULATE)
            
            self.client.publish(
                config.MQTT_TOPIC_STATUS, b"online", retain=True, qos=1
            )
            
            print("[INFO] MQTT connected and subscribed, status=online")
            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            print(f"[ERROR] MQTT connect failed: {e}")
            indicators.mqtt_error()
            return False

    def check_messages(self):
        """
        Poll the broker for any pending incoming messages.

        Must be called every main-loop iteration for timely delivery.
        Sets self.connected = False on any network error so the next
        publish() call will attempt reconnection.
        """
        if not self.connected:
            return
        try:
            self.client.check_msg()
        except OSError:
            self.connected = False

    def ping(self):
        """
        Send a MQTT PINGREQ to keep the broker session alive.

        Should be called on config.MQTT_PING_INTERVAL to prevent the
        broker from closing the connection due to keepalive timeout.
        """
        if self.connected:
            try:
                self.client.ping()
            except OSError:
                self.connected = False

    def publish(self, data):
        """
        Publish scan results as JSON to the telemetry topic.

        Triggers Wi-Fi or MQTT reconnection automatically if either
        link is down, then returns False so the caller can retry on
        the next scan cycle.

        Parameters
        ----------
        data : list
            Scan result list from WiFiScanner.get_results().

        Returns
        -------
        bool
            True on successful publish, False otherwise.
        """
        if not self.is_wifi_up():
            self.connect_wifi()
            return False
        if not self.connected:
            self.connect_mqtt()
            return False
        try:
            self.client.publish(config.MQTT_TOPIC_TELEMETRY, json.dumps(data))
            print("[INFO] Published telemetry")
            return True
        except OSError as e:
            self.connected = False
            print(f"[ERROR] Publish failed: {e}")
            return False