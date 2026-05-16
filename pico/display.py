from machine import Pin, I2C
import ssd1306

class DisplayManager:
    """
    Manages the OLED display (SSD1306) via I2C for showing Wi-Fi networks.
    Handles the rendering of interactive network lists with scrolling and detailed views.
    """
    
    def __init__(self, sda_pin=0, scl_pin=1, width=128, height=64):
        """
        Initializes the I2C interface and the SSD1306 display object.

        Args:
            sda_pin (int): GPIO pin number for I2C SDA (Serial Data Line).
            scl_pin (int): GPIO pin number for I2C SCL (Serial Clock Line).
            width (int): Display width in pixels.
            height (int): Display height in pixels.
        """
        self.i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
        self.oled = ssd1306.SSD1306_I2C(width, height, self.i2c)
        self.width = width
        self.height = height

    def clear(self):
        """Clears the display buffer by filling it with black pixels (0)."""
        self.oled.fill(0)

    def show(self):
        """Updates the physical display with the current buffer content."""
        self.oled.show()
        
    def draw_list(self, networks, selected_index):
        """
        Renders a scrollable list of Wi-Fi networks on the display.

        Args:
            networks (list): A list of dictionaries containing network info (e.g., 'ssid').
            selected_index (int): The index of the currently selected network in the list.
        """
        self.clear()
        
        # Draw header and a horizontal separator line
        self.oled.text("Wi-Fi Networks:", 0, 0)
        self.oled.hline(0, 10, self.width, 1)

        # Handle case where the network list is empty
        if not networks:
            self.oled.text("Scanning...", 0, 25)
            self.show()
            return
        
        # Calculate scrolling offset to keep the selected item visible
        # Limits the display to show up to 5 items at a time
        start_idx = max(0, selected_index - 4) # 0, 1, 2, 3, 4
        y = 15
        
        # Iterate through the visible slice of the networks list
        for i in range(start_idx, min(len(networks), start_idx + 5)):
            # Add a cursor indicator ('>') for the currently selected item
            prefix = "> " if i == selected_index else "  "
            self.oled.text(f"{prefix}{networks[i]['ssid']}", 0, y)
            y += 10 # Move down 10 pixels for the next line
            
        self.show()
        
    def draw_detail(self, network):
        """
        Renders a detailed view showing statistics for a single Wi-Fi network.

        Args:
            network (dict): Dictionary containing network details ('ssid', 'rssi', 'channel').
        """
        self.clear()
        
        # Handle case where an invalid network object is passed
        if not network:
            self.oled.text("No network selected", 0, 20)
            self.show()
            return

        # Draw header and a horizontal separator line
        self.oled.text("Network Detail:", 0, 0)
        self.oled.hline(0, 10, self.width, 1)
        
        # Display specific network properties
        self.oled.text(f"SSID: {network['ssid']}", 0, 15)
        self.oled.text(f"RSSI: {network['rssi']} dBm", 0, 27)
        self.oled.text(f"CH:   {network.get('channel', 'N/A')}", 0, 39)
        
        # Display a warning if the signal strength is critically low
        if network['rssi'] < -80:
            self.oled.text("! WEAK SIGNAL !", 0, 55)

        self.show()