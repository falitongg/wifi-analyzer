"""
MicroPython utility classes for handling button inputs with software debouncing.
Includes support for standard GPIO buttons and the Raspberry Pi Pico BOOTSEL button.
"""

from machine import Pin
import time
import rp2

class DebouncedButton:
    """
    A class to handle a standard GPIO button with software debouncing.
    Assumes the button is wired to connect the pin to ground when pressed (active-low).
    """
    
    def __init__(self, pin_num, debounce_ms=250):
        """
        Initialize the debounced button.
        
        Args:
            pin_num (int): The GPIO pin number the button is connected to.
            debounce_ms (int, optional): The debounce timeout in milliseconds. Defaults to 250ms.
        """
        # Configure the pin as an input with an internal pull-up resistor
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        self.debounce_ms = debounce_ms
        self.last_press = 0  # Stores the timestamp of the last successful button press
        
    def was_pressed(self):
        """
        Check if the button was pressed, ignoring physical bounces.
        
        Returns:
            bool: True if a valid, debounced press is detected, False otherwise.
        """
        # Check if the button is currently pressed (0 means pressed due to PULL_UP)
        if self.pin.value() == 0:
            current = time.ticks_ms()
            # Check if enough time has passed since the last registered press
            if time.ticks_diff(current, self.last_press) > self.debounce_ms:
                self.last_press = current  # Update the timestamp
                return True
        return False

class BootselButton:
    """
    A class to handle the built-in BOOTSEL button on the Raspberry Pi Pico 
    with software debouncing.
    """

    def __init__(self, debounce_ms=250):
        """
        Initialize the BOOTSEL button debouncer.
        
        Args:
            debounce_ms (int, optional): The debounce timeout in milliseconds. Defaults to 250ms.
        """
        self.debounce_ms = debounce_ms
        self.last_press = 0  # Stores the timestamp of the last successful button press

    def was_pressed(self):
        """
        Check if the BOOTSEL button was pressed, ignoring physical bounces.
        
        Returns:
            bool: True if a valid, debounced press is detected, False otherwise.
        """
        # rp2.bootsel_button() returns 1 when the BOOTSEL button is pressed
        if rp2.bootsel_button() == 1:
            current = time.ticks_ms()
            # Check if enough time has passed since the last registered press
            if time.ticks_diff(current, self.last_press) > self.debounce_ms:
                self.last_press = current  # Update the timestamp
                return True
        return False