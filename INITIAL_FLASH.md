# INITIAL_FLASH.md — Display zum ersten Mal flashen (per USB)

> **Wann diese Anleitung?** Genau **einmal pro Display**: wenn ein nagelneues (oder
> komplett geleertes) CYD zum ersten Mal Firmware bekommt. Dabei wird die **statische
> IP fix ins Gerät geschrieben**. Danach laeuft jeder weitere Flash **nur noch per OTA**
> ueber diese IP — siehe `README.md` § Deploy-Pipeline.
>
> **Diese Anleitung ist fuer jemanden ohne Vorwissen geschrieben.** Jeden Schritt der
> Reihe nach abarbeiten, nichts ueberspringen. Wenn ein Schritt fehlschlaegt → unten in
> § Troubleshooting nach der Fehlermeldung suchen, bevor du weitermachst.

---

## 0. Begriffe in einem Satz

- **USB-Flash** = Firmware ueber das USB-Kabel aufspielen. Pflicht beim allerersten Mal,
  weil das Geraet noch keine IP/keine OTA-Faehigkeit hat.
- **OTA** = "Over the Air", Flash uebers WLAN. Geht **erst nachdem** das Geraet einmal
  per USB geflasht wurde und unter seiner IP erreichbar ist.
- **Statische IP** = jedes Display hat eine feste, im Code hinterlegte IP (kein DHCP).
  Sie steht im Device-File und wird beim USB-Flash ins Geraet gebrannt.

---

## 1. Welches Display flashe ich? (Registry lesen)

Die Wahrheit steht in **`displays.yaml`**. Beispiel:

| logischer Name   | Device-File           | Hostname (Firmware) | IP             |
|------------------|-----------------------|---------------------|----------------|
| `cortex-terminal`| `cortex-terminal.yaml`| `cyd-panel`         | `192.168.1.240`|
| `cortex-vvo`     | `cortex-vvo.yaml`     | `cortex-vvo`        | `192.168.1.241`|

Merke dir aus der Zeile deines Displays: **das Device-File** und **die IP**. Beides
brauchst du gleich. Die IP wird automatisch aus dem Device-File gezogen — du musst sie
**nirgends von Hand eintippen**, nur am Ende zur Kontrolle vergleichen.

> **Woher kommt die IP technisch?** Im Device-File steht oben `substitutions: static_ip:`.
> Diese wird in `common/hardware.yaml` unter `wifi: manual_ip: static_ip:` eingesetzt.
> Beim Flash schreibt ESPHome das in die Firmware → das Display nimmt **immer** diese IP.

---

## 2. Voraussetzungen (einmalig einrichten)

Alle vier Checks muessen gruen sein, **bevor** du ein Kabel ansteckst. Das Helper-Skript
in Schritt 4 prueft sie nochmal automatisch — hier zum manuellen Nachvollziehen:

**a) esphome ist installiert**
```bash
which esphome && esphome version
```
Wenn nicht gefunden: `pip install --user esphome`

**b) `secrets.yaml` existiert** (liegt im Repo-Root, ist gitignored)
```bash
cat secrets.yaml
```
Muss mindestens enthalten:
```yaml
api_key:      "<base64 32-byte key>"
ota_password: "<dein-ota-passwort>"
```
Fehlt die Datei: aus dem GDrive-Backup (`secrets.yaml.bak-*`) wiederherstellen oder bei
Leo erfragen. **Ohne `secrets.yaml` bricht der Build sofort ab.**

**c) WLAN-Zugangsdaten als Env-Vars exportiert** (stehen NICHT in secrets.yaml)
```bash
export ESPHOME_WIFI_SSID="<dein-WLAN-Name>"
export ESPHOME_WIFI_PASSWORD="<dein-WLAN-Passwort>"
```
Diese gelten nur in der aktuellen Shell. Neue Shell = nochmal exportieren. Ohne sie
schlaegt der Build mit `Environment variable ... not defined` fehl.

**d) Du darfst auf den USB-Port zugreifen** (Linux: Gruppe `dialout`)
```bash
groups | grep -q dialout && echo "OK" || echo "FEHLT — siehe Troubleshooting"
```

---

## 3. Display anstecken und Port finden

1. CYD per **USB-Datenkabel** (kein reines Ladekabel!) an den Rechner stecken.
2. Seriellen Port finden:
   ```bash
   ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
   ```
   Erwartung: **genau ein** Eintrag, meist `/dev/ttyUSB0`.
   - **Nichts da?** → Troubleshooting "Kein Port".
   - **Mehrere?** → nur dein Display angesteckt lassen, andere USB-Serial-Geraete
     abziehen, damit eindeutig ist welcher Port gemeint ist.

---

## 4. Initial-Flash (per USB) — der eigentliche Schritt

**Empfohlen: Helper-Skript** (macht alle Preflight-Checks aus Schritt 2+3 automatisch,
findet den Port, zeigt dir die IP zur Bestaetigung):
```bash
./tools/initial_flash.sh cortex-terminal.yaml
```
Das Skript flasht **nicht** still drauflos: es zeigt erst Geraet, Hostname, IP und den
gefundenen Port und fragt nach Bestaetigung.

**Oder manuell**, falls du es lieber explizit machst:
```bash
esphome run cortex-terminal.yaml --device /dev/ttyUSB0
```
(Device-File durch deines ersetzen, Port falls noetig anpassen.)

**Erwarteter Log (Erfolg):**
```
INFO Successfully compiled program.
INFO Connecting via USB...
INFO Writing at 0x... (xx %)
INFO Hash of data verified.
INFO Leaving... / Hard resetting...
[I][app]: ESPHome version 2026.x.x compiled on ...
[I][wifi]: WiFi Connected ... IP: 192.168.1.240
```
Sobald `IP: 192.168.1.<deine>` im Log steht: **Flash war erfolgreich**, das Display hat
seine statische IP. `Ctrl-C` beendet das Live-Log (das Display laeuft weiter).

> **Wichtig:** Den Firmware-`name` (= Hostname, z.B. `cyd-panel`) **nie** aendern. Er
> ist in Home Assistant gepairt. Initial-Flash vergibt ihn einmal fix.

---

## 5. Verifizieren, dass das Display unter seiner IP erreichbar ist

USB-Kabel kann jetzt abgezogen werden (das Display braucht nur noch Strom). Dann:

```bash
# a) Erreichbar im Netz?
ping -c 3 192.168.1.240

# b) Web-Server (Port 80) antwortet?
curl -s http://192.168.1.240/ | head

# c) ESPHome-API offen? (exit 124 = Timeout = Port offen = OK)
timeout 2 bash -c 'cat < /dev/tcp/192.168.1.240/6053'; echo "exit=$?"
```

Alle drei gruen → **das Display ist fertig initialisiert**. In Home Assistant sollte die
ESPHome-Integration das Geraet jetzt unter seinem Hostnamen zeigen (ggf. Integration neu
laden, siehe `README.md` § Diagnose-Tree).

---

## 6. Ab jetzt: nur noch OTA

Das USB-Kabel wird nicht mehr gebraucht. Jeder weitere Flash laeuft uebers WLAN:
```bash
esphome run cortex-terminal.yaml --device 192.168.1.240
```
Details: `README.md` § Deploy-Pipeline. USB nur noch im Notfall (siehe `README.md`
§ USB-Recovery), z.B. bei api_key-Drift oder Crash-Loop.

---

## Troubleshooting

### Kein Port (`/dev/ttyUSB*` leer)
- Anderes USB-Kabel probieren — viele Kabel sind **nur Strom, keine Daten**.
- `dmesg | tail -20` direkt nach dem Einstecken: erscheint dort `ch341`, `cp210x` oder
  `ftdi`? Wenn nein, erkennt der Kernel den Seriell-Chip nicht → Kabel/Port wechseln.
- Manche CYDs brauchen den USB-Port direkt am Mainboard, nicht ueber einen Hub.

### `Permission denied` auf `/dev/ttyUSB0`
Du bist nicht in der Gruppe `dialout`:
```bash
sudo usermod -aG dialout $USER
```
Danach **ab- und wieder anmelden** (oder neu booten) — Gruppenwechsel greift erst dann.
Schneller Test ohne Logout: `newgrp dialout` in der aktuellen Shell.

### Build-Fehler `Environment variable "ESPHOME_WIFI_SSID" not defined`
Die WLAN-Env-Vars aus Schritt 2c sind in dieser Shell nicht gesetzt. Nochmal exportieren.

### Build-Fehler `secret 'api_key' not defined` / `secrets.yaml not found`
`secrets.yaml` fehlt oder ist unvollstaendig — Schritt 2b.

### Flash haengt bei `Connecting...` / `Failed to connect`
Das ESP haengt nicht im Bootloader-Modus:
- USB einmal ab- und wieder anstecken, Befehl erneut starten.
- Manche Boards: **BOOT-Taste gedrueckt halten** waehrend `Connecting...`, kurz nach
  Start des Flashs loslassen. (CYD ohne BOOT-Taste: Power-Cycle direkt vor dem Flash.)
- Sicherstellen, dass kein anderes Programm den Port belegt (z.B. ein offenes
  `esphome logs` in einem anderen Terminal).

### Display geflasht, aber `ping` schlaegt fehl
- Falsches WLAN: pruefe `ESPHOME_WIFI_SSID/PASSWORD` — das CYD haengt nur an 2.4-GHz-WLAN.
- IP-Konflikt: die statische IP ist evtl. schon vergeben. Gegen
  `~/cortex/docs/network-devices.md` pruefen; freie IP in `displays.yaml` **und** im
  Device-File (`substitutions: static_ip`) eintragen, dann erneut **per USB** flashen
  (IP-Aenderung greift nur ueber USB, da OTA die alte IP braucht).
- Im USB-Log nachsehen: steht dort `WiFi Connected`? Wenn nicht → WLAN-Problem, nicht IP.
</content>
</invoke>
