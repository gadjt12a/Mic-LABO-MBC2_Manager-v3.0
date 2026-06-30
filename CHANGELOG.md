# Changelog

All notable changes to MBC2 Dashboard are documented here.

---

## [3.3.0] — 2026-07-01

### Bidirectional Device Control

This release adds full bidirectional serial communication with the MBC2 device. You can now control the device entirely from the dashboard without touching the physical buttons.

### New Features

**Device Control Panel**
- START / STOP buttons for MANU mode
- PAUSE / RESUME with automatic button switching based on run_state
- NEXT STEP with confirmation dialog
- Voltage slider and input with live ACK-confirmed display
- Current limit input with SET button
- Direction toggle (R / N) with R visually emphasised
- START PROG to launch saved programs (1-50)
- Run state indicator showing device status (Running, Paused, Cooling, Overheat, etc.)

**Program Sync (GET_PROG / SET_PROG)**
- READ button fetches and decodes programs from device
- WRITE button encodes and sends programs to device RAM
- Full encoding/decoding support:
  - Program names (4-char, index 0-36 character table)
  - Non-linear time index (0-77 → 0s to 15h)
  - Voltage (internal × 0.1V)
  - Direction (0-4 ↔ OFF/N/R/NP/RP)
- Program display shows name, cycles, target RPM, and step table

**Device Settings (GET_SETTING / SET_SETTING)**
- READ ALL button fetches all 10 device settings
- Settings display with human-readable labels and units
- Settings editor modal for modifying values
- Per-setting SET buttons write individual settings to RAM
- Supported settings: overheat, limit_volt, limit_current, brightness, measure_step, cheer_up, pulse_v, pulse_sec, pulse_pattern, buzzer_volume

**SAVE TO EEPROM**
- Explicit button with confirmation warning
- Warns about EEPROM write cycle limits
- Never automatic — always user-initiated

**GET_LOG Integration**
- Automatic log retrieval when device stops
- Parses LOG:HEAD, LOG:STEP, LOG:CYC, LOG:END responses
- Displays per-step summary table (cycle, step, RPM, max RPM, voltage, current, temp)
- Overheat steps highlighted in red

**Auto Recording**
- Recording session auto-starts when START or START PROG clicked
- Recording auto-stops when STOP clicked

### Parser Improvements

- Serial parser now routes lines by prefix (STATUS / PROG / SETTING / LOG / CSV)
- Full run_state tracking (0=Running, 1=Paused, 2=Cooling, 3=Overheat, 5=Finished, 90=Over Current, 226=INA226 Error)
- STATUS message handler for ACKs, errors, and async notifications (COOLING, LOW_AMP_LIMIT)
- Debug lines properly ignored at parser entry point
- Fixed raw data column labels (col[13] is current_ma, not col[19])

### Other Changes

- Added .gitignore (excludes __pycache__, *.db-shm, *.db-wal)
- Added docs/ folder with technical documentation:
  - SERIAL_SPEC.md — full serial protocol specification
  - DB_SCHEMA.md — database schema reference
  - FEATURE_ROADMAP.md — feature implementation status
  - HARDWARE_REFERENCE.md — MBC2 device specs
  - VERSION_HISTORY.md — detailed version history
- Added CLAUDE.md for Claude Code project context

### Requirements

- **MBC2 firmware v0.110+** required for bidirectional features

---

## [3.0.0] — 2026-04-30

### Architecture — DB-only storage

All session and program data is now stored exclusively in `mbc2.db`. The `data/sessions/` CSV folder and `data/programs.json` file are no longer used. This eliminates the data loss issue caused by path resolution differences between launch locations and the fragile timestamp-based CSV matching that was used to retrieve session data.

### Breaking changes

- `POST /api/sessions` payload changed — now accepts `{ motor_id, session_type, notes, rows: [...] }` with parsed row objects instead of a CSV string. All session rows are written directly to the `session_data` table.
- `GET /api/sessions` now returns an array of session objects from the DB (with motor, peak RPM, row count) instead of a list of CSV filenames.
- `GET /api/sessions/<id>/data` — new endpoint, returns session rows from the DB by session ID.
- `GET /api/sessions/<id>/export` — new endpoint, generates a CSV on demand from DB rows for Excel export.
- `DELETE /api/sessions/<id>` — now accepts a numeric session ID (was a filename string).
- `GET /api/programs` and `POST /api/programs` (JSON file endpoints) removed. Program library is read and written via `/api/profiles` and `/api/profiles/import` exclusively.

### server.py

- Removed all `DATA_DIR`, `sessions_dir`, and `programs.json` file handling.
- `POST /api/sessions` writes rows to `session_data` table and optionally records a benchmark and break-in log entry in the same request.
- `GET /api/sessions` returns DB session list.
- `GET /api/sessions/<id>/export` streams a CSV generated from the DB.
- `DELETE /api/sessions/<id>` cascades deletion through `session_data`, `benchmarks`, and `motor_breakin_log`.
- Seed file lookup simplified — looks in app root only, no `data/` subfolder search.

### db_manager.py

- `DB_PATH` now uses `Path(__file__).resolve().parent` — database is always found relative to the script file regardless of the working directory Python is launched from. This was the root cause of the data disappearing between sessions.
- Added `get_all_sessions()` — returns all sessions with motor identifier, model, peak RPM, benchmark type, and row count.
- Added `delete_session(session_id)` — cascades through `session_data`, `benchmarks`, and `motor_breakin_log`.
- Added `export_session_csv(session_id)` — generates a CSV string from `session_data` rows on demand, no file written to disk.
- Added `parse_mbc2_row(raw_line, session_id, timestamp_ms)` — parses a raw MBC2 serial CSV line into a `session_data` row dict.

---

## Prior development history

This repo starts at v3.0.0. The following is a condensed summary of the development that took place in the previous repository before the architecture was stable enough to version properly.

**v0.4.0 — 2026-04-26**
Target RPM reference line on live chart. kV curve in benchmark results panel. Motor comparison side-by-side stats table and RPM overlay for up to 5 sessions. Session notes and ambient temperature fields. Per-step cooldown timer in sidebar. Pre-treatment structured dropdown replacing freetext field.

**v0.3.0 — 2026-04-24**
SQLite motor registry database introduced (`mbc2.db`). Motors tab added alongside Charts and Raw Data. Motor registration with auto-generated identifiers (`SD-R-01` format). Full Tamiya motor lineup and chassis assignment. Break-in program linking.

**v0.2.0 — 2026-04-23**
Moved to server-based architecture (`server.py` on port 8766). Program library drawer with full profile and program CRUD. MBC2 Entry Guide modal. Active program selector with persistence. Firmware version checker.

**v0.1.0–v0.1.2 — 2026-04-23**
Initial build. Web Serial API connection to MBC2 at 115200 baud. Live RPM, Amps, Voltage, kV efficiency, and Temperature charts. Session recording. Serial column mapping confirmed from live capture.
