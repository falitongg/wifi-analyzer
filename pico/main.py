"""
Entry point for the Pico W Wi-Fi monitor.

Enhanced version with comprehensive diagnostic logging and automatic
UI updates when data arrives.
"""

from machine import Pin
import time
import ntptime
import config
from display import DisplayManager
from buttons import DebouncedButton, BootselButton
import indicators
from wlan_manager import WLANManager
from wifi_scanner import WiFiScanner
from mqtt_manager import MQTTManager

# --- Hardware ---
led = Pin("LED", Pin.OUT)
led.value(1)

display = DisplayManager(
    scl_pin=config.SCL_PIN,
    sda_pin=config.SDA_PIN,
    width=config.WIDTH,
    height=config.HEIGHT,
)

btn_next    = DebouncedButton(config.BTN_NEXT_PIN, config.DEBOUNCE_DELAY)
btn_bootsel = BootselButton(config.DEBOUNCE_DELAY)

# --- Subsystems ---
wlan    = WLANManager()
mqtt    = MQTTManager(wlan)

# --- Application state ---
wifi_data    = []
current_mode = "LIST"
selected_idx = 0
time_synced  = False

last_scan_request_ms = 0
last_mqtt_ping_ms    = 0
last_ui_update_ms    = 0
last_wlan_status_log = -999  # log status changes (avoid spam)
last_mqtt_check_ms   = 0     # log MQTT status periodically
last_ntp_attempt = 0

# Flag to trigger UI update from callback
_pending_ui_update = False

# --- Display initial state ---
display.draw_list(wifi_data, selected_idx)
print("[INFO] Display initialized, waiting for first scan...")

# ------------------------------------------------------------------
# Scan completion callback
# ------------------------------------------------------------------
def on_scan_complete(results):
    """Scan finished; update state and flag UI for refresh."""
    global wifi_data, selected_idx, current_mode, _pending_ui_update

    print(f"[SCAN] Completed: found {len(results)} networks")

    selected_ssid = None
    if wifi_data and 0 <= selected_idx < len(wifi_data):
        selected_ssid = wifi_data[selected_idx]['ssid']

    wifi_data = results

    if selected_ssid and wifi_data:
        for i, net in enumerate(wifi_data):
            if net['ssid'] == selected_ssid:
                selected_idx = i
                print(f"[SCAN] Re-selected: {selected_ssid}")
                break
        else:
            selected_idx = 0
            if current_mode == "DETAIL":
                current_mode = "LIST"
                print(f"[SCAN] Selected network disappeared; returning to LIST")
    else:
        selected_idx = 0

    # Trigger UI update on next loop iteration
    _pending_ui_update = True

    # Attempt MQTT publish if connected
    if not mqtt.is_wifi_up():
        print("[MQTT] Wi-Fi not up; requesting connect")
        mqtt.connect_wifi()
    elif mqtt.connected:
        payload = {
            "timestamp": get_timestamp() if time_synced else None,
            "networks": wifi_data
            }
        if mqtt.publish(payload):
            print(f"[MQTT] Published {len(results)} networks with timestamp")
        else:
            print("[MQTT] Publish failed")
    else:
        print("[MQTT] Not connected; attempting connect")
        mqtt.connect_mqtt()

# NTP synchronization
def ntp_sync():
    ntptime.host = "192.168.137.1"
    ntptime.settime()
    print("[NTP] NTP synced: " + get_timestamp())

# Timestamp ISO 8601
def get_timestamp():
    t = time.gmtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.000Z".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        )

scanner = WiFiScanner(wlan, on_data_ready=on_scan_complete)

# ------------------------------------------------------------------
# Main loop
# ------------------------------------------------------------------
while True:
    indicators.update()
    mqtt.check_messages()

    # Execute one queued WLAN operation
    wlan.process()
    
    # If a scan just completed, force UI update immediately
    # (don't wait for timer)
    if _pending_ui_update:
        # fall through to rendering section below
        pass

    current_time   = time.ticks_ms()
    need_ui_update = False
    
    if mqtt.is_wifi_up() and not time_synced:
        if time.ticks_diff(current_time, last_ntp_attempt) > 10000:
            try:
                ntp_sync()
                time_synced = True
            except Exception as e:
                print(f"[ERROR] NTP sync failed: {e}")


    # --- DETAIL view refresh ---
    if current_mode == "DETAIL" and \
            time.ticks_diff(current_time, last_ui_update_ms) > 200:
        need_ui_update    = True
        last_ui_update_ms = current_time

    # --- Queue new scan on interval ---
    if time.ticks_diff(current_time, last_scan_request_ms) > config.SCAN_INTERVAL:
        print(f"[SCAN] Requesting scan (interval {config.SCAN_INTERVAL}ms)")
        scanner.request_scan()
        last_scan_request_ms = current_time
        need_ui_update = True

    # --- Periodic WLAN status logging ---
    wlan_status = wlan.raw_status()
    if wlan_status != last_wlan_status_log:
        status_names = {
            0: "IDLE",
            1: "CONNECTING",
            3: "GOT_IP",
            -2: "CONNECT_FAIL",
            -1: "INVALID",
        }
        status_name = status_names.get(wlan_status, f"UNKNOWN({wlan_status})")
        print(f"[WLAN] Status changed: {status_name} ({wlan_status})")
        last_wlan_status_log = wlan_status

    # --- MQTT keepalive ping ---
    if time.ticks_diff(current_time, last_mqtt_ping_ms) > config.MQTT_PING_INTERVAL:
        mqtt.ping()
        last_mqtt_ping_ms = current_time

    # --- Periodic MQTT status log ---
    if time.ticks_diff(current_time, last_mqtt_check_ms) > 5000:
        wifi_ok = "yes" if mqtt.is_wifi_up() else "no"
        mqtt_ok = "yes" if mqtt.connected else "no"
        print(f"[STATUS] Wi-Fi: {wifi_ok}, MQTT: {mqtt_ok}")
        last_mqtt_check_ms = current_time

    # --- Button: cycle networks ---
    if btn_next.was_pressed() and wifi_data:
        selected_idx   = (selected_idx + 1) % len(wifi_data)
        need_ui_update = True
        print(f"[BTN] Next: {wifi_data[selected_idx]['ssid']}")

    # --- Button: toggle LIST/DETAIL ---
    if btn_bootsel.was_pressed():
        current_mode   = "DETAIL" if current_mode == "LIST" else "LIST"
        need_ui_update = True
        print(f"[BTN] Mode: {current_mode}")

    # --- Render UI ---
    # Force update if pending from callback, or if conditions above say to update
    need_ui_update = need_ui_update or _pending_ui_update
    _pending_ui_update = False

    if need_ui_update:
        try:
            if current_mode == "LIST":
                indicators.clear_rssi()
                display.draw_list(wifi_data, selected_idx)
                if not wifi_data:
                    print("[UI] List: empty (still scanning)")
                else:
                    print(f"[UI] List: {len(wifi_data)} networks")

            elif current_mode == "DETAIL" and wifi_data:
                display.draw_detail(wifi_data[selected_idx])
                rssi = wifi_data[selected_idx]["rssi"]
                print(f"[UI] Detail: {wifi_data[selected_idx]['ssid']} ({rssi} dBm)")
                if rssi < -80:
                    indicators.bad_rssi()
                else:
                    indicators.good_rssi()
                    indicators.stop_beep()
        except Exception as e:
            print(f"[ERROR] UI render failed: {e}")


