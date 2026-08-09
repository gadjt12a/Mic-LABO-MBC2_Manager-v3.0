# MBC2 Dashboard

Data logger, program library, motor registry, and full bidirectional device control for the **mic-LABO Motor Boot Camp 2 (MBC2)** motor break-in machine. Built for the Mini 4WD racing community.

---

## Download

| Platform | Package | Notes |
|---|---|---|
| **Windows** | `MBC2Dashboard-Setup-<version>.exe` | Installer — recommended |
| **Windows** | `MBC2Dashboard-WindowsPortable-<version>.zip` | USB / portable — no install needed |
| **Mac** | `MBC2Dashboard-Mac-<version>.zip` | Source package — UNTESTED disclaimer inside |

Download from the [GitHub Releases](../../releases) page.

> **No GitHub release has been published yet.** `v4.0` is tagged, but tagging
> does not upload artefacts and `dist/` is not in the repository. Until a
> release is cut, the packages have to be built from source — see
> [`BUILD.md`](BUILD.md).

---

## Requirements

**Every platform:**

- **CH340 driver** — needed for the MBC2 USB connection
  - Download: https://www.wch-ic.com/downloads/CH341SER_EXE.html
  - **ARM64 users (Surface Pro X, Copilot+ PCs):** install exactly **v3.9.2024.9** — newer versions dropped ARM64 support
- **MBC2 firmware v0.110+** for bidirectional control features

**Windows installer / portable:** nothing else. The app runs in its own window
— no browser and no Python needed.

**Mac / run from source:** Python 3.8+, the `pyserial` package, and a web
browser. Chrome and Edge are what we test; other modern browsers should work.

---

## Windows — Installer

1. Download `MBC2Dashboard-Setup-<version>.exe`
2. Run it (click **More info → Run anyway** if SmartScreen appears)
3. A desktop icon is created; launch it
4. The dashboard opens in its own window — pick your MBC2's COM port and click **Connect MBC2**

Your motor database is stored at `%LOCALAPPDATA%\MBC2Dashboard\mbc2.db` and is **never touched by the installer**.

## Windows — USB / Portable

1. Download and unzip `MBC2Dashboard-WindowsPortable-<version>.zip`
2. Read `README.txt` inside the zip
3. Double-click **`Start MBC2 (USB).bat`** to store data on the stick, or **`Start MBC2 (this PC).bat`** to use your PC's standard data folder

## Mac

1. Download and unzip `MBC2Dashboard-Mac-<version>.zip`
2. Read `README.txt` inside the zip
3. Right-click **`Start MBC2 Dashboard.command`** → Open → Open (required on first
   launch — the package is unsigned, and macOS may claim it "is damaged", which
   it is not)
4. The launcher ships with its execute bit set. If macOS still says it cannot be
   executed: `chmod +x "Start MBC2 Dashboard.command"` in Terminal

**The Mac package has never been run on a Mac.** It is structurally verified
only — see [`BUILD.md`](BUILD.md).

---

## Run from source

```
git clone <repo-url>
cd Mic-LABO-MBC2_Manager-v3.0
pip install -r requirements.txt
python3 app/server.py
```

Requires Python 3.8+. Opens `http://127.0.0.1:8766` in your browser.

`pyserial` is the only requirement for talking to the device. To run the
native-window version instead of a browser tab, also `pip install pywebview`
and run `python3 app/app.py` (Windows/Mac desktop only).

---

## Features

- **Live monitoring** — real-time RPM, Amps, kV efficiency, temperature charts
- **Device control** — START / STOP / PAUSE / RESUME / NEXT STEP / voltage / current limit / direction
- **Break-in programs run from the app** — pick one of your programs and press START PROG; the app drives the device through each step (direction, voltage, run time, cool period) for the set number of cycles
- **Program library** — create, edit and store break-in profiles; import/export JSON
- **Program sync** — read all 50 device slots in one action, save one into your library, or write a program to a slot so the MBC2 can run standalone without the laptop (RAM only; the device's saved programs are never overwritten)
- **Motor registry** — register motors, track break-in history, compare sessions
- **AccelTest results** (firmware v0.200+) — the device's own AccelTest is
  captured automatically and shown per motor: RPM at three load levels with the
  current measured at each, plus load retention (high-load ÷ no-load), the
  figure that separates motors peak RPM cannot. The test is started on the
  device; the app records what it sends
- **Benchmark mode** — automated voltage ramp with per-step kV results and efficiency rating
- **Crash log** — silence watchdog captures full motor state on unexpected data gaps
- **Connection tracking** — records each USB connection lifecycle

---

## Project layout

```
app/        app.py, server.py, db_manager.py, motor_api.py, mbc2-dashboard.html
            schema.sql, default_programs.json, VERSION, icon.ico, splash.png
windows/    MBC2Dashboard.iss, BUILD EXE.bat, BUILD INSTALLER.bat
            installer-info.txt, USB launcher bats, README.txt
mac/        Start MBC2 Dashboard.command, BUILD MAC PACKAGE.bat,
            make-mac-zip.ps1, README.txt
tests/      test_program_timing.js (run with node; developer tool only)
docs/       SERIAL_SPEC.md, DB_SCHEMA.md, FEATURE_ROADMAP.md, VERSION_HISTORY.md
```

See [`BUILD.md`](BUILD.md) for developer build instructions.

---

## Serial protocol

Full MBC2 bidirectional serial specification: [`docs/SERIAL_SPEC.md`](docs/SERIAL_SPEC.md)

The dashboard talks to the device from the Python backend via **pyserial** at
115200 baud. Incoming lines are streamed to the UI over Server-Sent Events
(`/api/serial/stream`); commands go out over `POST /api/serial/send`.

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
