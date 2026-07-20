# MBC2 Dashboard

Data logger, program library, motor registry, and full bidirectional device control for the **mic-LABO Motor Boot Camp 2 (MBC2)** motor break-in machine. Built for the Mini 4WD racing community.

---

## Download

| Platform | Package | Notes |
|---|---|---|
| **Windows** | `MBC2Dashboard-Setup-4.0.exe` | Installer — recommended |
| **Windows** | `MBC2Dashboard-WindowsPortable-4.0.zip` | USB / portable — no install needed |
| **Mac** | `MBC2Dashboard-Mac-4.0.zip` | Source package — UNTESTED disclaimer inside |

Download from the [GitHub Releases](../../releases) page.

---

## Requirements (all platforms)

- **Chrome or Edge** — Web Serial API is required; Firefox and Safari will not work
- **CH340 driver** — needed for the MBC2 USB connection
  - Download: https://www.wch-ic.com/downloads/CH341SER_EXE.html
  - **ARM64 users (Surface Pro X, Copilot+ PCs):** install exactly **v3.9.2024.9** — newer versions dropped ARM64 support
- **MBC2 firmware v0.110+** for bidirectional control features

---

## Windows — Installer

1. Download `MBC2Dashboard-Setup-4.0.exe`
2. Run it (click **More info → Run anyway** if SmartScreen appears)
3. A desktop icon is created; launch it
4. Chrome or Edge opens at `http://127.0.0.1:8766` — connect your MBC2

Your motor database is stored at `%LOCALAPPDATA%\MBC2Dashboard\mbc2.db` and is **never touched by the installer**.

## Windows — USB / Portable

1. Download and unzip `MBC2Dashboard-WindowsPortable-4.0.zip`
2. Read `README.txt` inside the zip
3. Double-click **`Start MBC2 (USB).bat`** to store data on the stick, or **`Start MBC2 (this PC).bat`** to use your PC's standard data folder

## Mac

1. Download and unzip `MBC2Dashboard-Mac-4.0.zip`
2. Read `README.txt` inside the zip
3. Right-click **`Start MBC2 Dashboard.command`** → Open → Open (required on first launch)
4. If macOS says it cannot be executed: `chmod +x "Start MBC2 Dashboard.command"` in Terminal

---

## Run from source

```
git clone <repo-url>
cd Mic-LABO-MBC2_Manager-v3.0
python3 app/server.py
```

Requires Python 3.8+. No external dependencies. Opens `http://127.0.0.1:8766` in your browser.

---

## Features

- **Live monitoring** — real-time RPM, Amps, kV efficiency, temperature charts
- **Device control** — START / STOP / PAUSE / RESUME / NEXT STEP / voltage / current limit / direction
- **Program sync** — read and write device program slots (GET_PROG / SET_PROG)
- **Program library** — create, edit and store break-in profiles; import/export JSON
- **Motor registry** — register motors, track break-in history, compare sessions
- **Benchmark mode** — automated voltage ramp with per-step kV results and efficiency rating
- **Crash log** — silence watchdog captures full motor state on unexpected data gaps
- **Connection tracking** — records each USB connection lifecycle

---

## Project layout

```
app/        server.py, db_manager.py, motor_api.py, mbc2-dashboard.html
            schema.sql, default_programs.json, VERSION, icon.ico
windows/    MBC2Dashboard.iss, BUILD EXE.bat, BUILD INSTALLER.bat
            installer-info.txt, USB launcher bats, README.txt
mac/        Start MBC2 Dashboard.command, BUILD MAC PACKAGE.bat, README.txt
docs/       SERIAL_SPEC.md, DB_SCHEMA.md, FEATURE_ROADMAP.md, VERSION_HISTORY.md
```

See [`BUILD.md`](BUILD.md) for developer build instructions.

---

## Serial protocol

Full MBC2 bidirectional serial specification: [`docs/SERIAL_SPEC.md`](docs/SERIAL_SPEC.md)

The dashboard communicates via **Web Serial API** at 115200 baud (Chrome / Edge only).

---

## Motor direction reference

All Tamiya Mini 4WD chassis break in at **Reverse (R)** on the MBC2.

| Mount | Chassis examples |
|---|---|
| Front | FM-A, Super FM |
| Rear | MA, MS, AR, VS, VZ, Super-II, Super-X, Zero, Type 1–5 |
| Midship (dual shaft) | ME, MA, MS |

---

*Created by Kris Pawson. Device and firmware by Michihiro Nakagawa (mic-LABO).*
