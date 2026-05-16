from machine import Pin, PWM
import time
import rp2
import config

led_green = Pin(config.GREEN_PIN, Pin.OUT)
led_red = Pin(config.RED_PIN, Pin.OUT)

buzzer = PWM(Pin(config.BUZZER_PIN))
buzzer.freq(config.FREQUENCY)
buzzer.duty_u16(0)


last_timer_beep = 0
last_timer_green = 0
last_timer_red = 0

def update():
    global last_timer_beep, last_timer_green, last_timer_red
    current = time.ticks_ms()
    
    if last_timer_beep != -1 and time.ticks_diff(current, last_timer_beep) >= 0:
        stop_beep()
        
    if last_timer_green != 0 and time.ticks_diff(current, last_timer_green) >= 0:
        led_green.value(0)
        last_timer_green = 0
        
    if last_timer_red != 0 and time.ticks_diff(current, last_timer_red) >= 0:
        led_red.value(0)
        last_timer_red = 0

def beep(duration_ms=300):
    global last_timer_beep
    buzzer.duty_u16(32768)
    
    if duration_ms < 0:
        last_timer_beep = -1
    else:
        last_timer_beep = time.ticks_add(time.ticks_ms(), duration_ms)

def stop_beep():
    global last_timer_beep
    buzzer.duty_u16(0)
    last_timer_beep = 0
    
def network_status(connected):
    global last_timer_green, last_timer_red
    if connected:
        led_green.value(1)
        last_timer_green = time.ticks_add(time.ticks_ms(), 100)
    else:
        led_red.value(1)
        last_timer_red = time.ticks_add(time.ticks_ms(), 100)
        
def mqtt_error():
    death()
        
def bad_rssi():
    led_green.value(0)
    led_red.value(1)
    beep(-1)
    
def good_rssi():
    led_red.value(0)
    led_green.value(1)
    stop_beep()
    
def clear_rssi():
    led_green.value(0)
    led_red.value(0)
    stop_beep()
    
def death():
    global last_timer_red
    led_red.value(1)
    beep(5000)
    last_timer_red = time.ticks_add(time.ticks_ms(), 5000)
