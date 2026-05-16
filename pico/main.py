from machine import Pin
import time
import config
from display import DisplayManager
from buttons import DebouncedButton, BootselButton
import indicators
from wifi_scanner import WiFiScanner
from mqtt_manager import MQTTManager

led = Pin("LED", Pin.OUT)
led.value(1)

display = DisplayManager(scl_pin=config.SCL_PIN, sda_pin=config.SDA_PIN, width=config.WIDTH, height=config.HEIGHT)

btn_next = DebouncedButton(config.BTN_NEXT_PIN, config.DEBOUNCE_DELAY)
btn_bootsel = BootselButton(config.DEBOUNCE_DELAY)

scanner = WiFiScanner()
wifi_data = []

mqtt = MQTTManager()
mqtt.connect_wifi()
mqtt.connect_mqtt()

current_mode = "LIST"  # LIST" or "DETAIL" state
selected_idx = 0

last_wifi_scan_time = 0
last_mqtt_ping = 0

last_ui_update = 0
display.draw_list(wifi_data, selected_idx)

while True:
    indicators.update()
    current_time = time.ticks_ms()
    need_screen_update = False
    
    if current_mode == "DETAIL" and time.ticks_diff(current_time, last_ui_update) > 40:
        need_screen_update = True
        last_ui_update = current_time

    if time.ticks_diff(current_time, last_wifi_scan_time) > config.SCAN_INTERVAL:
        selected_ssid = None
        if wifi_data and 0 <= selected_idx < len(wifi_data):
            selected_ssid = wifi_data[selected_idx]['ssid']
        
        wifi_data = scanner.scan()
        last_wifi_scan_time = current_time
        
        mqtt.publish_data(wifi_data)
        last_mqtt_ping = current_time
        
        if selected_ssid and wifi_data:
            found = False
            for i, net in enumerate(wifi_data):
                if net['ssid'] == selected_ssid:
                    selected_idx = i
                    found = True
                    break
            
            if not found:
                if current_mode == "DETAIL":
                    current_mode = "LIST"
        else:
            selected_idx = 0
            
        need_screen_update = True

    if time.ticks_diff(current_time, last_mqtt_ping) > config.MQTT_PING_INTERVAL:
        mqtt.ping()
        last_mqtt_ping = current_time

    if btn_next.was_pressed():
        selected_idx = (selected_idx + 1) % len(wifi_data)
        need_screen_update = True

    if btn_bootsel.was_pressed():
        current_mode = "DETAIL" if current_mode == "LIST" else "LIST"
        need_screen_update = True

    if need_screen_update:
        if current_mode == "LIST":
            indicators.clear_rssi()
            display.draw_list(wifi_data, selected_idx)
        elif current_mode == "DETAIL":
            display.draw_detail(wifi_data[selected_idx])
            
            current_rssi = wifi_data[selected_idx]["rssi"]
            if current_rssi < -80:
                indicators.bad_rssi()
            else:
                indicators.good_rssi()
                indicators.stop_beep()
