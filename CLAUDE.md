# MBC2 Dashboard — Claude Code Project Context

## What this project is

A personal, non-commercial open-source tool for logging, managing, and analysing motor break-in sessions using the **mic-LABO Motor Boot Camp 2 (MBC2)** device. Built for the Mini 4WD racing community. Published free on GitHub.

The MBC2 is an ESP32-WROOM-32 based device that drives motors through break-in programs and streams telemetry over USB serial (CH340 chip, 115200 baud).

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | Vanilla JS, single HTML file (`mbc2-dashboard.html`) |
| Database | SQLite (`mbc2.db`) |
| Serial | Web Serial API (Chrome only, 115200 baud) |
| Host | Windows (Microsoft Surface X, ARM64) |

**Working directory:** `C:\Users\Kris.Pawson\projects\Mic-LABO-MBC2_Manager-v3.0\`

---

## Current version: v3.3

See [`docs/VERSION_HISTORY.md`](docs/VERSION_HISTORY.md) for full history.

Key architectural facts:
- Fully DB-only storage (no CSV files). All session data goes to SQLite.
- `connections` table tracks device connection lifecycle.
- `sessions` table has `connection_id` FK, `duration_sec`, `end_reason`.
- `crash_events` table captures full motor state snapshots on unexpected silence.
- JS silence watchdog fires after 30 seconds of no data while recording.
- Loop/round tracking: `loop_number`, `max_loop`, `prog_loop`, `prog_max_loop` captured in session data and crash events.

---

## Reference documents

| Document | Purpose |
|---|---|
| [`docs/SERIAL_SPEC.md`](docs/SERIAL_SPEC.md) | Full MBC2 serial interface — commands, responses, CSV format, encodings |
| [`docs/DB_SCHEMA.md`](docs/DB_SCHEMA.md) | SQLite schema, migration patterns, column reference |
| [`docs/FEATURE_ROADMAP.md`](docs/FEATURE_ROADMAP.md) | Planned features, priority order, what's deferred |

---

## Hard rules — read before touching anything

### General

- **Incremental changes only.** Do not rewrite large sections of code wholesale. Make targeted, minimal changes.
- **The frontend is a single file** (`mbc2-dashboard.html`). Do not split it into multiple files.
- **Web Serial API is intentionally Chrome-only.** Do not attempt to add Node.js serial or other browser compatibility.
- **Serial baud rate is 115200.** Do not change this.
- **The CH340 driver required is v3.9.2024.9** (ARM64). Newer versions dropped ARM64 support. Do not reference or suggest driver upgrades.

### Database / schema migrations

- **Always use `CREATE TABLE IF NOT EXISTS`** — never `CREATE TABLE`.
- **Always use `_add_column_if_missing()` helper** for adding columns to existing tables. Never use raw `ALTER TABLE ADD COLUMN` without this guard.
- **Never drop or rename columns.** Add new ones; leave old ones in place.
- Schema must auto-migrate safely on app launch against existing databases.

### Serial parser

- **Ignore lines prefixed with `Debug:`** — the MBC2 firmware emits these and they will be removed in a future firmware version. Never parse or store them.
- **Distinguish by prefix:** CSV data lines have no prefix. STATUS responses start with `STATUS:`. Program data starts with `PROG:`. Settings start with `SETTING:`. Log data starts with `LOG:`. Anything else is ignored.
- **`STATUS:OK:SET_VOLTAGE:v` echoes the clamped actual value**, not the requested value. Always read the ACK response and use its value to update state — do not assume the requested voltage was applied.
- **`STATUS:OK:SET_CURRENT_LIMIT:a`** similarly echoes the clamped actual value.

### Command safety

- **`SAVE` command writes to EEPROM.** EEPROM has a finite write cycle life. Never call `SAVE` automatically or on a timer. It must always be an explicit deliberate user action. Warn the user before sending it.
- **`SET_PROG` changes are RAM-only** until `SAVE` is sent. Make this clear in any UI that edits programs.
- **Program numbers are 1–50 only.** Program No.0 (MANU) cannot be read or written via `GET_PROG`/`SET_PROG`. Always validate before sending.

### Domain rules

- **Correct break-in direction for all Mini 4WD chassis is `R` (Reverse).** This applies to FM-A, Super-FM, MA, MS, and all other Tamiya chassis. `N` (Normal) is not used for racing break-in.
- **The Christchurch club break-in programs (PMPE, SPRF) are private club knowledge.** They must NEVER be included in `default_programs.json` or any seed data shipped with the app. They are distributed only as a separate importable `christchurch_protocol.json`.
- **Motor identifiers follow the format `MODEL-DIRECTION-NUMBER`** (e.g. `SD-R-01`). Sequential numbering resets per model code.

### Flask route ordering

- In `motor_api.py`, specific routes must be defined **before** generic catch-all routes.
- The generic `GET /api/motors/<identifier>` must come **after** routes like `/api/motors/roster`.
- Violating this causes Flask to intercept specific routes with the generic handler.

### Data columns — common mistakes

- **`col[13]` (`current_ma`)** — instantaneous current in mA, exponential smoothing already applied by firmware. Use directly.
- **`col[19]` (`total_rotations`)** — cumulative rotation count (`log_rotate_total ÷ 1000`). This is **rotations, not charge**. Do not refer to it as a charge accumulator.
- **`col[7]` (`current_rpm`)** and **`col[8]` (`max_rpm`)** — already actual RPM values (internal value × 10 done by firmware). No further multiplication needed.

---

## External collaborator

**Michihiro Nakagawa** (mic-LABO) created and maintains the MBC2 device and firmware. He has implemented the bidirectional serial interface documented in `docs/SERIAL_SPEC.md`.

Communication approach with Michihiro:
- Present only observed facts. No personal theories.
- Keep requests minimal and practical.
- Iterate incrementally — don't ask for multiple changes at once.
