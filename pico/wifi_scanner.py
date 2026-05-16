import network
import time
import indicators

class WiFiScanner:
    
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.previous_ssids = set()
        
    def scan(self):
        raw_results = self.wlan.scan()
        
        current_ssids = set()
        formatted_results = []
        
        for net in raw_results:
            try:
                ssid = net[0].decode('utf-8')
                if not ssid:
                    continue
                
                channel = net[2]
                rssi = net[3]
                
                current_ssids.add(ssid)
                formatted_results.append({
                    'ssid': ssid,
                    'rssi': rssi,
                    'channel': channel
                })
            except UnicodeError:
                pass
            
        new_networks = current_ssids - self.previous_ssids
        lost_networks = self.previous_ssids - current_ssids
        
        if new_networks:
            indicators.network_status(True)
        elif lost_networks:
            indicators.network_status(False)

        self.previous_ssids = current_ssids
        
        return formatted_results

