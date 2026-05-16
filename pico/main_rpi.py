from machine import Pin, I2C
import ssd1306

led = Pin("LED", Pin.OUT)
led.toggle()

scl = Pin(21)
sda = Pin(20)

i2c = I2C(0, sda=sda, scl=scl, freq=400000)


WIDTH = 128
HEIGHT = 64

oled = ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)


oled.fill(0)
oled.text("Pico is ALIVE!", 0, 0)
oled.text("Pins: GP20 / GP21", 0, 20)
oled.show()


