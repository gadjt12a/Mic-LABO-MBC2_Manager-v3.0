# MBC2 Dashboard

Data logger, program library, motor registry, and **full bidirectional device control** for the mic-LABO Motor Boot Camp 2 (MBC2) motor break-in machine.

## Features

### Live Monitoring
- Real-time serial data logging from MBC2 via USB (Web Serial API)
- Live charts — RPM, Amps, kV efficiency, Temperature
- Target RPM reference line on live RPM chart from the active program
- Per-step cooldown timer — sidebar shows live COOLING countdown between program steps
- Run state indicator (Running, Paused, Cooling, Overheat, Finished)

### Bidirectional Device Control (NEW in v3.3)
- **START / STOP / PAUSE / RESUME** — control the device directly from the dashboard
- **Voltage control** — slider and input with live ACK-confirmed value display
- **Current limit** — set CC limit with confirmation feedback
- **Direction toggle** — switch between R (Reverse) and N (Normal)
- **START PROG** — launch any saved program (1-50) from the dashboard
- **NEXT STEP** — skip to next step with confirmation
- **Program sync** — read/write device programs via GET_PROG/SET_PROG
- **Device settings** — view and edit all device settings (overheat temp, voltage limits, etc.)
- **SAVE TO EEPROM** — persist changes with confirmation warning
- **GET_LOG** — automatic run summary retrieval when program stops

### Program Library
- Create, edit and store break-in profiles and programs
- MBC2 Entry Guide — step-by-step reference for entering programs on the device
- Import/export profiles as JSON

### Motor Registry
- Register and track individual motors with persistent SQLite database
- Auto-generated identifiers (e.g. `SD-R-01`)
- Benchmark mode — records a 1.0→3.0V voltage ramp with per-step kV results
- Motor comparison — side-by-side stats and RPM overlay for up to 5 sessions
- Efficiency rating (A/B/C/D) based on RPM and current draw

### Session Management
- All data saved to `mbc2.db` — no CSV files to manage
- Auto-start recording when device starts
- Auto-stop recording when device stops
- CSV export available on demand
- Firmware version checker and download links

## Requirements

- Python 3.8 or higher
- Chrome or Edge browser (Web Serial API required — Firefox/Safari not supported)
- MBC2 connected via USB (CH340 driver may need to be installed)
- **MBC2 firmware v0.110+** for bidirectional control features

## Getting Started

**Windows:** Double-click `START MBC2 DASHBOARD.bat`

**Mac:** Right-click `Start MBC2 Dashboard.command` → Open (required on first launch due to Gatekeeper)

The script starts the local server and opens the dashboard in your default browser at `http://localhost:8766`.

> If you open `mbc2-dashboard.html` directly without running the launcher, the Motor Registry and Program Library will not save — you will see connection errors in the console.

## Files

```
MBC2_Dashboard/
├── mbc2-dashboard.html          ← main app (open via localhost:8766)
├── server.py                    ← local API server (started by the launcher)
├── db_manager.py                ← database functions
├── motor_api.py                 ← motor registry API routes
├── schema.sql                   ← SQLite schema (applied automatically on first run)
├── mbc2.db                      ← single database for all app data (created on first run)
├── default_programs.json        ← break-in profiles seeded into DB on first run
├── seed_programs.json           ← additional profiles seeded into DB on first run
├── START MBC2 DASHBOARD.bat     ← Windows launcher
├── Start MBC2 Dashboard.command ← Mac launcher
├── CLAUDE.md                    ← Claude Code project context
├── docs/                        ← technical documentation
│   ├── SERIAL_SPEC.md           ← full serial protocol specification
│   ├── DB_SCHEMA.md             ← database schema reference
│   ├── FEATURE_ROADMAP.md       ← feature implementation status
│   ├── HARDWARE_REFERENCE.md    ← MBC2 device and Mini 4WD context
│   └── VERSION_HISTORY.md       ← detailed version changelog
├── README.md
└── CHANGELOG.md
```

## Device Control Panel

The right sidebar now includes a **Device Control** section with:

| Control | Function |
|---------|----------|
| START | Start MANU mode |
| STOP | Stop motor and save log |
| PAUSE / RESUME | Pause/resume current run (button changes based on state) |
| NEXT | Skip to next step (with confirmation) |
| Voltage slider | Adjust voltage in real-time (0-9V) |
| Current limit | Set CC limit (0=OFF, up to 4.5A) |
| Direction | Toggle R (Reverse) / N (Normal) |
| START PROG | Launch a saved program by number (1-50) |
| READ / WRITE | Sync programs with device |
| SAVE TO EEPROM | Persist RAM changes to permanent storage |
| Device Settings | View and edit all device configuration |

## Motor Registry

The Motors tab lets you register and track individual motors across their entire life cycle.

### Motor identifier format

`MODEL-DIRECTION-NUMBER` — e.g. `SD-R-01`, `PD-R-02`, `HD3-R-01`

Print on 12mm label tape, cut to 5mm, stick on motor end bell.

### Chassis direction reference

All Tamiya Mini 4WD chassis run the motor in **Reverse (R)** on the MBC2 as the race direction.

| Mount | Chassis | Break-in direction |
|-------|---------|-------------------|
| Front | FM-A, Super FM, FM | **R (Reverse)** |
| Rear | VZ, AR, VS, Super TZ-X, Super TZ, Super XX, Super X, Super-II, Super-1, Zero, Type 1–5 | **R (Reverse)** |
| Midship (dual shaft) | ME, MA, MS | **R (Reverse)** |

## Program Library

Click **☰ Programs** in the header to open the program library drawer.

Pre-populated with:
- **Baseline** — standard 5-step 1.0→3.0V benchmark ramp
- **Stock Motor** — 3-cycle brush seating for kit standard motors
- **Torque Tuned 2** — 3-stage break-in (A: seating, B: wake up, C: polish)
- **Hyper Dash** — 3-stage break-in for high-RPM dash motors

## Serial Protocol

The dashboard now implements the full MBC2 bidirectional serial protocol. See `docs/SERIAL_SPEC.md` for the complete specification including:

- CSV telemetry stream format (20 columns)
- All commands (START, STOP, PAUSE, RESUME, SET_VOLTAGE, etc.)
- Program read/write encoding (GET_PROG, SET_PROG)
- Settings read/write (GET_SETTING, SET_SETTING)
- Run log retrieval (GET_LOG)

## Hardware

- ESP32-WROOM-32, 240MHz, 4MB flash
- INA226 current sensor
- CH340 USB-serial at 115200 baud
- **Firmware v0.110+** required for bidirectional features
- OTA firmware updates via `http://[MBC2-IP]/u`
