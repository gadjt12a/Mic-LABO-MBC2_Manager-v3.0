# Changelog

All notable changes to MBC2 Dashboard are documented here.

---

## [4.0.1] — unreleased

### Added

- **AccelTest results are captured and displayed** (firmware v0.200+). AccelTest
  measures the RPM a motor holds at three fixed current draws; it is started on
  the device, so the app watches for `ACCEL_*` lines and records what arrives.
  Results appear under Motors → AccelTest and on each motor's own record, showing
  No / Low / High load RPM per direction with the current measured at each, the
  test voltage, and **load retention** (high-load ÷ no-load) as the headline
  figure. The raw serial lines are stored verbatim alongside the parsed values so
  a later decode can be applied to tests already recorded.
- A test run with no motor selected is saved unattributed rather than discarded,
  and can be attached to a motor afterwards from the AccelTest tab.
- New API routes: `POST /api/accel/save`, `GET /api/accel[?motor_id=n]`,
  `POST /api/accel/<id>/motor`, `DELETE /api/accel/<id>`.
- New tables `accel_tests` and `accel_test_passes`, auto-created on launch.

### Fixed

- **Break-in program steps could run long if the window was not in front.**
  Step timing was a bare `setTimeout`, and browsers throttle timers in a
  hidden or occluded window — Chrome aligns them to roughly one-minute wake-ups
  after five minutes hidden. Since that timer is what ends a step, minimising
  the app during a run could leave the motor powered well past the time the
  program specified, with nothing to show it had happened. The deadline is now
  wall-clock and is also checked on every telemetry row (SSE delivery is not
  throttled) and when the window becomes visible again. If a step does end late
  anyway, it is reported during the run and again at the end — a run whose steps
  overran did not follow the program it claims to have followed.

- **The Mac package zip was malformed and probably unusable.** `Compress-Archive`
  wrote backslash path separators into it, which the zip spec forbids; macOS can
  extract such an archive as flat files literally named
  `MBC2Dashboard\app\server.py`, leaving the launcher unable to find
  `app/server.py`. The v4.0.1 Mac zip has this defect. It is now built by
  `mac\make-mac-zip.ps1`, which writes spec-clean entries, sets the Unix execute
  bit on the launcher so it no longer needs a manual `chmod +x`, and fails the
  build if either check regresses. (`tar.exe` was tried first and rejected — it
  pads past the end-of-central-directory record.) Mac remains untested on real
  hardware; this fixes a defect found by inspection, not by running it.
- The Mac launcher now carries its execute bit in git (`100755`).
- Mac README: documented the "is damaged and can't be opened" wording that macOS
  shows for an unsigned app on first launch, since it is alarming and false.

- **Startup wasted ~3 seconds proving the port was free.** The already-running
  and port-in-use checks each blocked on a connection to a closed loopback
  port. This machine does not refuse those promptly — a blocking `connect_ex`
  takes ~2.0s to return `WSAECONNREFUSED` and the urllib probe burned its full
  1s timeout — so every launch paid ~3s against ~0.04s of real startup work.
  Now a single probe with a short timeout answers all three cases (free, ours,
  foreign); a real listener accepts in ~2ms, so nothing slower is a running
  instance. Startup from source went 3.38s → 0.62s, and the packaged exe from
  4.8s → 1.9s warm (the rest is PyInstaller unpacking ~21MB).

---

## [4.0] — 2026-08-07

Packaging release: installer, portable/USB build, Mac package, and a move off
the browser's Web Serial API.

### Added

- **Windows installer** (`MBC2Dashboard-Setup-4.0.exe`, Inno Setup, per-user)
  and **portable/USB zip** with `Start MBC2 (USB).bat` for data-on-the-stick.
- **Native window** — `app/app.py` starts the server on a background thread,
  waits for `/api/ping`, then opens a pywebview window. No browser needed on
  Windows. PyInstaller splash dismissed on page load.
- **COM port dropdown** with refresh button, replacing Chrome's port picker.
- **Separate data home** — `%LOCALAPPDATA%\MBC2Dashboard\` (Mac:
  `~/Library/Application Support/MBC2Dashboard/`), overridable with
  `MBC2_DATA_DIR` (this is how USB mode works). Installers can no longer
  reach the database.
- **Automatic daily backups** via SQLite's backup API, last 14 kept.
- **One-time legacy migration** — a `mbc2.db` beside the app is copied (never
  moved) into the new data home, leaving `DATA-HAS-MOVED.txt` behind.
- `app/VERSION` as the single source of truth, served via `GET /api/info`.
- `requirements.txt` (pyserial).
- **Run break-in programs from the app.** Selecting a program under "In this
  app" and pressing START PROG makes the app drive the device step by step
  over serial — direction, voltage, run time, cool period, repeated for the
  cycle count — with STOP, PAUSE and NEXT acting on that run. Nothing is
  written to the device. Programs stored in the device's own slots remain
  runnable directly (`START_PROG:n`) as an alternative.
- **Read All Slots** (⟳ ALL) reads all 50 device slots in one action; empty
  slots are hidden from the run list. There is no `GET_PROG:ALL` on the
  device, so this walks the slots.
- **Save to Library** turns a program read off a device into a stored app
  program — for a program built standalone, or copied from someone else's
  device.
- **Device replies are checked.** A rejected program write, a device that
  fails to start, or a voltage clamped by `limit_volt` is now reported rather
  than passing silently. A clamped step raises a warning showing what was
  asked for and what was applied.
- **Unsaved rows are protected on exit.** Closing the window mid-recording
  asks first, and only when there are actually rows to lose. Connection
  records are closed when the app exits rather than left open.

### Changed

- **Serial moved from the browser to Python.** `SerialManager` in
  `app/server.py` owns the port via pyserial; the UI drives it through
  `/api/ports`, `/api/serial/connect`, `/api/serial/disconnect`,
  `/api/serial/send`, and an SSE stream at `/api/serial/stream`. Chrome is no
  longer required — from source, any modern browser works.
- **Program controls unified.** The app's own programs and the device's slot
  programs now sit in one `Break-in Program` section, labelled "In this app"
  and "On the device". `PAUSE` and `NEXT` moved there from Device Control,
  since they act on a running program; Device Control keeps the manual-run
  controls (START/STOP, voltage, current limit, direction).
- **Device slots are for standalone use, not for running programs.** Writing
  a program into a slot lives in Settings → Program Sync, and exists so the
  MBC2 can be run on the bench without the laptop, or so a program can be
  imported. It is still **RAM-only — `SAVE` is never sent** — and slots are
  validated 1–50 so program 0 (MANU) can never be overwritten.
- **Baseline 3.0V** is a single 3-minute 3.0V step in R, and runs like any
  other program. It was previously two 2-minute steps either side of a cool
  period, the first of which ran in F.
- All API calls are same-origin. They previously targeted
  `http://localhost:8766` while the page is served from `127.0.0.1:8766`,
  which forced a CORS preflight on every request.
- **Manual motor runs are recorded.** Pressing START auto-starts a session,
  but every row was discarded while the device reported `MANU` — the recorder
  was waiting for a named program to begin, so manual runs always saved an
  empty session. Manual runs are now recognised and recorded; the wait-for-
  program behaviour is unchanged for program runs.
- Repo restructured into `app/`, `windows/`, `mac/`, `docs/`; root launchers
  and the old per-platform setup guides absorbed into per-platform READMEs.
- Browser/window opens only after the socket is bound, replacing a fixed
  0.8 s timer. A foreign program on port 8766 now gets a plain-English message
  box instead of a traceback.

### Fixed

- Non-Chromium browser warning banner no longer fires in the packaged app —
  the old `'serial' in navigator` check disabled the Connect button in the
  native window, where that API does not exist.
- "No COM ports found" banner now actually appears when the port list is
  empty (it was being reset to its CSS `display:none`).
- **Right-hand side of the window was cut off on scaled displays.** The
  process did not declare DPI awareness, so Windows sized the window in
  physical pixels while WebView2 laid the page out in CSS pixels and scaled
  it up — on a 125% display a 1400 px window received ~1750 px of content,
  hiding Clear, Stop Server and the whole device-control column with no
  reflow. `app/app.py` now sets per-monitor-v2 DPI awareness before creating
  the window, and clamps the window to the desktop work area so it cannot
  open taller than the screen.
- **App-library programs had no steps.** `/api/profiles` returned program
  metadata without the step list, so every program in the library loaded with
  an empty `steps` array — anything that converted a library program produced
  one with no voltages or timings.
- **Selecting a program in the dropdown selected nothing.** The dropdown wrote
  string ids while the library holds numbers, and every lookup uses strict
  equality. The program name, target RPM and the remembered program across
  restarts were all affected.
- **Baseline 3.0V vanished from the program dropdown.** Two functions built
  the same `<select>` and the one without the Baseline entry overwrote the one
  with it, which made benchmark mode unreachable — no benchmark had ever been
  recorded.
- **Programs restarted the motor at every step.** `START` was sent per step,
  so the motor stopped and spun back up at each boundary and the device's own
  log was reset, leaving `LOG:` describing only the final step.
- **Connection records were never closed on exit.** The page closed them from
  a `pagehide` beacon, which could not work: the beacon went to a different
  origin and was dropped, and in the packaged app `os._exit(0)` killed the
  server before it could be served. The server now closes the record itself.
- **Closing the window mid-recording discarded rows silently.** WebView2
  ignores `beforeunload`, so the page's own warning never appeared.

### Known gaps

- USB/portable mode has not been exercised on a second machine.
- The Mac package is untested on real hardware.
- No full 3-minute baseline benchmark has been recorded.
- SmartScreen click-through screenshots are not yet captured.

---

## [3.4.2] — 2026-07-20

### Phase 4 — Program launch panel

#### Added

- **START PROGRAM dropdown** — replaced the raw slot-number input with a named
  `<select>` that populates from the `devicePrograms` cache. Each entry shows
  `[n] NAME` for every program read via Settings → Program Sync. When no
  programs have been synced the dropdown shows "no programs synced" and a hint
  directs the user to Program Sync.
- `updateStartProgDropdown()` — called automatically whenever a `PROG:` response
  arrives so the launcher stays in sync with the cache without user action.

---

## [3.4.1] — 2026-07-20

### Code Review Fixes & UX Polish

Full code review pass: critical session-save bug fixed, server hardened, UX improved.

### Fixed

- **Session save flow** — telemetry rows never reached the database (missing
  `session_id` binding caused every save to fail after the session record was
  created), and each recorded run created two session records. Rows, benchmarks,
  and CSV export now converge on one session. Empty duplicate records cleaned out.
- **Settings tab program read** — reading a program slot from the device now
  actually displays it (was rendering into a non-existent element).
- Motor identifier numbering past 99 (was a string sort).
- Settings-loaded toast count derived from metadata instead of hardcoded 10.

### Changed

- Server binds `127.0.0.1` only (was all interfaces with open CORS) and serves
  requests on threads so the firmware-version fetch can't freeze the app.
- `mbc2.db` removed from git; `*.db` ignored (privacy: personal data and
  imported club programs must never be published).
- Native `confirm()`/`alert()` replaced with styled modals; destructive actions
  get red action-specific buttons.

### New

- Server health dot in header (polls `/api/ping`); loud toast when the backend
  goes offline.
- Tab-close protection: warning mid-recording; connection record closed via
  `sendBeacon` on tab close.
- Chart axis labels (scale max/mid + visible time span).
- UI Scale control (90–125%) in Extras menu.
- Voltage slider clamps to the device's `limit_volt` after settings are read.
- `_add_column_if_missing()` migration helper; dead code removed
  (`parse_mbc2_row` and friends).
- `DEPLOYMENT_PLAN.md` — draft v4 packaging plan (Windows installer / USB / Mac).

---

## [3.4.0] — 2026-07-03

### Crash Log & Connection Tracking

This release adds crash detection and connection lifecycle tracking for debugging MBC2 stability issues during testing.

### New Features

**Connection Tracking**
- New `connections` table records each USB serial connection
- Tracks connection start time, end time, and end reason (normal/crash)
- Sessions linked to their parent connection for context

**Crash Log**
- New `crash_events` table captures motor state snapshots on data loss
- Silence watchdog monitors for 30+ seconds of no serial data during recording
- Auto-logs crash event with full state: voltage, current, RPM, kV, temp, program step
- Crash Log tab shows all events with connection context and session history
- Delete individual crash events

**UI Improvements**
- New **Extras** dropdown menu in tab bar
- Raw Data and Crash Log tabs moved under Extras to declutter main navigation
- Main tabs now: Charts, Programs, Motors, Settings

### Code Cleanup

- Removed orphaned roster table code (filterRoster, sortRoster, renderRoster)
- Removed unused CSS classes for roster table
- Simplified loadRoster() to only fetch data for rating badges
- Added setActiveMotorFromDetail() to replace removed function

### Database

- Added `connections` table with auto-migration
- Added `crash_events` table with auto-migration
- Updated DB_SCHEMA.md documentation

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
