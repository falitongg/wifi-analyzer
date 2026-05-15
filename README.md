# Wi-Fi Signal Monitor – Semestrální projekt NSI

**Autor:** Anton Sokolov (sokolant), B0B37NSI<br>
**Hardware:** Raspberry Pi Pico W<br>
**Jazyk:** MicroPython, Python (Dashboard)<br>
**Protokol:** MQTT (publish/subscribe), HTTP/REST

---

## Popis projektu

Wi-Fi Signal Monitor je autonomní IoT zařízení postavené na platformě Raspberry Pi Pico W. Zařízení kontinuálně skenuje okolní Wi-Fi sítě, měří sílu jejich signálu (RSSI v dBm) a poskytuje uživateli lokální i vzdálenou diagnostiku.

Systém je navržen pro běh v izolované lokální síti (hotspot notebooku) s využitím lokálního MQTT brokeru (Mosquitto). Data jsou vizualizována na webovém dashboardu ve formě histogramu všech viditelných sítí. Webový dashboard navíc slouží jako interaktivní řídicí panel, pomocí kterého lze vzdáleně konfigurovat periodu mezi jednotlivými skeny (v rozmezí od 5 do 150 sekund), nebo skenování na zařízení zcela vypnout.

---

## Uživatelské rozhraní (Hardware UI)

Zařízení je vybaveno interaktivním ovládáním a vizuální signalizací:

1. **Hlavní tlačítko (GP12):** Slouží k procházení seznamu nalezených sítí na OLED displeji. Stisk posune kurzor (`>`) dolů; po dosažení konce seznamu se kurzor vrátí na začátek.
2. **Tlačítko BOOTSEL:** Přepíná mezi režimem **Přehled** (seznam sítí s kurzorem) a režimem **Detail** (podrobné informace o síti vybrané kurzorem).
3. **LED Indikace:**
* **Zelená LED:** Rozsvítí se na 1 sekundu, pokud je v novém skenu detekována síť, která v předchozím nebyla (nový uzel v dosahu).
* **Červená LED:** Rozsvítí se na 1 sekundu, pokud některá ze sítí z předchozího skenu zmizela.


4. **Aktivní bzučák:** V režimu **Detail** vydává varovný signál při poklesu RSSI pod kritickou mez (-80 dBm).

---

## Softwarová architektura a Data Flow

### 1. Embedded část (Pico W)

Mikrokontrolér provádí periodické skenování (`wlan.scan()`). Interval skenování lze dynamicky měnit (od 5 do 150 sekund) nebo jej lze na základě příkazu z dashboardu zcela pozastavit. Po každém skenu:

* Porovná aktuální SSID s předchozím stavem pro aktivaci LED.
* Aktualizuje OLED displej (zobrazuje Top-4 sítě, počítadlo skenů a kurzor).
* Odešle kompletní pole nalezených sítí na MQTT broker.
* Naslouchá MQTT zprávám pro změnu konfigurace (změna periody, vypnutí/zapnutí skenování).

**Topic:** `nsi/wifi-monitor/telemetry`

**Payload (JSON Array):**

```json
[
  {"ssid": "Eduroam", "rssi": -65},
  {"ssid": "MyLaptopHotspot", "rssi": -45},
  {"ssid": "TP-Link_12", "rssi": -82}
]


```

### 2. Webový Dashboard (Flask)

* **Backend:** Odebírá zprávy z MQTT a ukládá poslední stav do mezipaměti. Zároveň odesílá konfigurační příkazy zpět do Pico W.
* **API:** Poskytuje endpoint `/api/data` pro frontend.
* **Frontend:** Pomocí JavaScriptu a knihovny **Chart.js** vykresluje sloupcový graf (Bar Chart), kde osa X představuje SSID a osa Y sílu signálu.
* **Vzdálená správa (Řízení zařízení):** Přímo v uživatelském rozhraní dashboardu má uživatel možnost nastavit prodlevu (periodu) mezi jednotlivými skeny v rozsahu 5 až 150 sekund a také funkci skenování na Pico W jednoduše úplně vypnout (případně znovu zapnout).

---

## Hardware a zapojení

| Komponenta | Zapojení |
| --- | --- |
| Raspberry Pi Pico W | Řídící jednotka |
| OLED displej 128×64 | I2C: SDA=GP0, SCL=GP1 |
| LED zelená | GP15 + 100Ω rezistor |
| LED červená | GP14 + 100Ω rezistor |
| Aktivní bzučák | GP13 |
| Mikrospínač | GP12 (interní pull-up) |
| Tlačítko BOOTSEL | Integrované (přepínání režimů) |

---

## Instalace a spuštění

1. **MQTT Broker:** Spusťte Mosquitto na notebooku (v rámci Wi-Fi hotspotu).
2. **Pico W:** Nastavte IP adresu notebooku v `config.py` a nahrajte kód.
3. **Dashboard:**

```bash
pip install flask paho-mqtt
python app.py


```

4. Otevřete `http://localhost:5000` pro zobrazení histogramu a správu skenování.

---

## Struktura repozitáře

```text
wifi-signal-monitor/
├── pico_code/
│   ├── main.py
│   ├── config.py
│   ├── wifi_scanner.py
│   ├── display.py
│   ├── indicators.py
│   └── lib/ (ssd1306.py, umqtt.simple.py)
├── dashboard/
│   ├── app.py
│   └── templates/
│       └── index.html
└── README.md


```