from machine import Pin
import time
import config
from display import DisplayManager
from buttons import DebouncedButton, BootselButton

led = Pin("LED", Pin.OUT)
led.value(1)

display = DisplayManager(scl_pin=config.SCL_PIN, sda_pin=config.SDA_PIN, width=config.WIDTH, height=config.HEIGHT)

btn_next = DebouncedButton(config.BTN_NEXT_PIN, config.DEBOUNCE_DELAY)
btn_bootsel = BootselButton(config.DEBOUNCE_DELAY)

current_mode = "LIST"  # LIST" or "DETAIL" state
selected_idx = 0

last_wifi_scan_time = 0
last_mqtt_ping = 0


wifi_data = [
    {"ssid": "Eduroam", "rssi": -65, "channel": 1},
    {"ssid": "Home_Network", "rssi": -45, "channel": 6},
    {"ssid": "Free_WiFi", "rssi": -85, "channel": 11},
    {"ssid": "Hidden_Net", "rssi": -72, "channel": 3},{"ssid": "Hidden_Net", "rssi": -72, "channel": 3},{"ssid": "Hidden_Net", "rssi": -72, "channel": 3},
]

display.draw_list(wifi_data, selected_idx)
while True:
    current_time = time.ticks_ms()
    need_screen_update = False

    if time.ticks_diff(current_time, last_wifi_scan_time) > SCAN_INTERVAL:
        # TODO
        last_wifi_scan_time = current_time

    if time.ticks_diff(current_time, last_mqtt_ping) > MQTT_PING_INTERVAL:
        # TODO
        last_mqtt_ping = current_time

    if btn_next.was_pressed():
        selected_idx = (selected_idx + 1) % len(wifi_data)
        need_screen_update = True

    if btn_bootsel.was_pressed():
        current_mode = "DETAIL" if current_mode == "LIST" else "LIST"
        need_screen_update = True

    if need_screen_update:
        if current_mode == "LIST":
            display.draw_list(wifi_data, selected_idx)
        elif current_mode == "DETAIL":
            display.draw_detail(wifi_data[selected_idx])

