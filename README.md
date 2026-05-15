
# Wi-Fi Signal Monitor – Semestrální projekt NSI

**Autor:** Anton Sokolov (sokolant), B0B37NSI <br>
**Hardware:** Raspberry Pi Pico W<br>
**Jazyk:** MicroPython, Python (Dashboard)<br>
**Protokol:** MQTT (s autentizací), HTTP/REST<br>
**Databáze:** SQLite3<br>

---

## Popis projektu

Wi-Fi Signal Monitor je autonomní IoT zařízení postavené na platformě Raspberry Pi Pico W. Zařízení kontinuálně skenuje okolní Wi-Fi sítě, měří sílu jejich signálu (RSSI v dBm) a poskytuje uživateli lokální i vzdálenou diagnostiku.

Systém využívá lokální MQTT broker (Mosquitto) se zabezpečeným přístupem. Data jsou odesílána na Flask server, kde se **ukládají do SQLite databáze** pro zpětnou analýzu a následně se vizualizují na webovém dashboardu. Dashboard slouží také jako řídicí panel pro konfiguraci periody skenování (5–150 s) nebo jeho úplné vypnutí.

---

## Uživatelské rozhraní (Hardware UI)

Zařízení je vybaveno interaktivním ovládáním a vizuální signalizací:

1. **Hlavní tlačítko (GP12):** Procházení seznamu sítí na OLED displeji.
2. **Tlačítko BOOTSEL:** Přepínání mezi režimem **Přehled** (seznam) a **Detail** (podrobné info o vybrané síti).
3. **LED Indikace:**
* **Zelená LED:** Detekce nové sítě v dosahu (trvá 1 s).
* **Červená LED:** Zmizení sítě z dosahu (trvá 1 s).
* **Chybový stav:** Pokud dojde k selhání spojení s MQTT brokerem, **rozsvítí se obě LED současně**.


4. **Aktivní bzučák:** Varovný signál v režimu Detail při poklesu RSSI pod -80 dBm.

---

## Softwarová architektura a Data Flow

### 1. Embedded část (Pico W)

Mikrokontrolér provádí periodické skenování a odesílá data na MQTT broker.

* **Robustnost:** V případě výpadku spojení Pico W automaticky zahajuje proces opětovného připojení (re-connect logic).
* **Zabezpečení:** Klient se k brokeru připojuje pomocí jména a hesla.
* **MQTT Topic:** `nsi/wifi-monitor/telemetry`

### 2. Webový Dashboard (Flask) & Backend

* **MQTT Subscriber:** Přijímá JSON data a ukládá je do **SQLite databáze** (tabulka `wifi_logs` s časovou značkou, SSID a RSSI).
* **API:** Poskytuje endpoint `/api/data` pro aktuální stav a historické trendy.
* **Ošetření chyb:** Pokud dashboard neobdrží data po dobu delší než dvojnásobek nastavené periody, uživatelské rozhraní zobrazí stav **"Device Offline"**.

---

## Zabezpečení a robustnost

* **Autentizace:** MQTT broker vyžaduje ověření uživatele. Pico W i Flask backend používají přihlašovací údaje definované v `config.py`.
* **Persistence:** Díky SQLite jsou data uchována i po restartu serveru.
* **Chybové stavy:** Systém je navržen tak, aby nezamrzl při ztrátě Wi-Fi signálu nebo nedostupnosti brokera; Pico se aktivně pokouší o obnovu spojení, zatímco dashboard informuje uživatele o výpadku.

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

---

## Instalace a spuštění

1. **MQTT Broker:** 
    * Spusťte Mosquitto s povolenou autentizací (`allow_anonymous false`).
    * Vytvořte uživatele pomocí `mosquitto_passwd`.


2. **Pico W:** 
    * V souboru `config.py`/`secrets.json` nastavte SSID, heslo k Wi-Fi a **MQTT credentials**.
    * Nahrajte kód do zařízení.


3. **Dashboard:**
```bash
pip install flask paho-mqtt sqlite3
python app.py

```


    * Aplikace při prvním spuštění automaticky vytvoří soubor `database.db`.



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
│   ├── app.py (Flask + SQLite logika)
│   ├── database.db (auto-generated)
│   └── templates/
│       └── index.html
└── README.md

```