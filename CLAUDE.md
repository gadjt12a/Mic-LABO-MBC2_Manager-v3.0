# MBC2 Dashboard — Claude Code Project Context

## What this project is

A personal, non-commercial open-source tool for logging, managing, and analysing motor break-in sessions using the **mic-LABO Motor Boot Camp 2 (MBC2)** device. Built for the Mini 4WD racing community. Published free on GitHub.

The MBC2 is an ESP32-WROOM-32 based device that drives motors through break-in programs and streams telemetry over USB serial (CH340 chip, 115200 baud).

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python stdlib `http.server` (+ `pyserial`; `pywebview` for the packaged window) |
| Frontend | Vanilla JS, single HTML file (`app/mbc2-dashboard.html`) |
| Database | SQLite (`mbc2.db` in `%LOCALAPPDATA%\MBC2Dashboard\` for packaged; beside `app/` for dev) |
| Serial | Server-side `pyserial` at 115200 baud; lines pushed to the UI over SSE |
| Window | `pywebview` native window (packaged exe); browser at `127.0.0.1:8766` (from source / Mac) |
| Host | Windows (Microsoft Surface X, ARM64) |

**Working directory:** `C:\kris\Projects\Mic-LABO-MBC2_Manager-v3.0\`

**Repo layout (v4):**
- `app/` — all source files: `app.py` (pywebview entry point), `server.py`, `db_manager.py`, `motor_api.py`, `mbc2-dashboard.html`, `schema.sql`, `default_programs.json`, `VERSION`, `icon.ico`, `splash.png`
- `windows/` — Windows build scripts, Inno Setup script, USB launcher bats, READMEs
- `mac/` — Mac launcher, Mac package build script, Mac README
- `docs/` — technical reference docs (unchanged)

---

## Current version: 4.0.1 (all work on `main`)

`v4.0` was tagged 2026-08-07; `main` has since moved to 4.0.1. The
`v4-packaging` branch is fully merged and dead — **do not look for work there**.
Version comes from `app/VERSION` alone: it drives `/api/info`, the footer, and
every artefact filename, so bump it there and nowhere else. See
[`DEPLOYMENT_PLAN.md`](DEPLOYMENT_PLAN.md) for test-matrix and release status.

**Serial is server-side; the packaged app is a native window.** Phase 4.5
(commit `fa9cc1f`) moved serial out of the browser and into Python. The old
"no native window — ever" rule existed only because WebView2 lacks the Web
Serial API; that constraint no longer applies and the rule is withdrawn.

- Packaged exe → `app/app.py` starts the server on a thread, waits for
  `/api/ping`, then opens a `pywebview` window. **No browser is required.**
- From source and on Mac → `app/server.py` is the entry point and the UI opens
  in a browser. Any modern browser works (serial no longer needs Chrome), but
  Chrome/Edge is what gets tested.

See [`docs/VERSION_HISTORY.md`](docs/VERSION_HISTORY.md) for full history.

Key architectural facts:
- Serial lives in `SerialManager` (`app/server.py`), exposed as `/api/ports`,
  `/api/serial/connect`, `/api/serial/disconnect`, `/api/serial/send`, and
  `/api/serial/stream` (SSE). The frontend holds no serial port object.
- `pyserial` is imported behind a `try/except` — the app still starts without
  it and reports `pyserial not installed` on connect.
- Fully DB-only storage (no CSV files). All session data goes to SQLite.
- `connections` table tracks device connection lifecycle.
- **`sessions` does NOT have `connection_id`, `duration_sec` or `end_reason`** —
  this file and `docs/DB_SCHEMA.md` both claimed it did until 2026-08-09, and
  neither the schema nor any live database has ever had those columns. The table
  is `session_id, motor_id, session_type, session_date, notes, ambient_temp_c`.
  A consequence: sessions are not linked to connections at all, so
  `connections.total_sessions` is 0 on every row. Check `app/schema.sql` before
  writing a query against `sessions`.
- `crash_events` table captures full motor state snapshots on unexpected silence.
- JS silence watchdog fires after 30 seconds of no data while recording.
- Loop/round tracking: `loop_number`, `max_loop`, `prog_loop`, `prog_max_loop` captured in session data and crash events.
- **The app is the program engine.** Running a break-in program does not involve
  the device's program slots at all. `startAppProgram()` walks the steps itself
  — `START`, then `SET_DIRECTION` / `SET_VOLTAGE` per step, `STOP` for cool
  periods — exactly as a manual run would. STOP/PAUSE/NEXT act on that run.
- **Two kinds of program, and they are not interchangeable.** The app library
  holds programs you design (`programLibrary.profiles[].programs[]`, shape
  `{volts, dir, time:"0:30", cool:"0:00"}`); the device holds 50 slots read via
  `GET_PROG` into `devicePrograms`. Device slots exist for **standalone use** —
  running the MBC2 on the bench without the laptop — and for importing a
  program someone else built. They are an alternative input, not the way
  programs are run. `START_PROG:n` still runs a device slot directly.
- **Device slot contents are not persistent app state.** They live only in
  `devicePrograms`, so they must be re-read (⟳ ALL) after every connect. Empty
  slots answer `GET_PROG` with a blank name and all steps at 0.0V/OFF/0s;
  `isDeviceProgramEmpty()` is the test, and the dropdown hides them.
- Manual (MANU) runs are recorded via the `manualRun` flag. The MANU guard in the data handler exists to skip idle frames while waiting for a program to start, and must stay in place for program runs.
- **AccelTest cannot be started by the app, and no amount of looking will find
  the command.** Firmware v0.200+ has an AccelTest in the device's own menu;
  there is no serial command for it, so the app is purely passive — it watches
  for `ACCEL_*` lines in `handleAccelMessage()` and records what arrives. Do not
  add a "run AccelTest" button.
- **A completed AccelTest with no motor selected is saved anyway**, with
  `accel_tests.motor_id` NULL and a warning toast. That is deliberate: the test
  costs minutes of motor time and is not worth discarding for a tidy schema.
  `POST /api/accel/<id>/motor` claims it afterwards, which is the only reason
  the AccelTest tab has an attach dropdown.
- **Store the current beside every AccelTest RPM.** The device derives its three
  load levels *per motor* — a Torque-Tuned 2 drew 313 mA where a box stock drew
  749 mA at the same "no-load" level. Without `*_ma`, two motors measured at
  very different loads both read as "no-load" and look comparable when they are
  not.
- **AccelTest voltage comes from CSV `col11`, sampled from before the test
  starts.** `col11` reads 0 while the device drives its own load ramp, so
  watching it from the first `ACCEL_` line onward records the wrong value — it
  logged 1500 mV for a 3.0 V test. `lastSetVoltageMv` is tracked continuously in
  `parseCSVTelemetry` for exactly this reason.
- **Storing raw lines is not total insurance, and `test_voltage_mv` proves it.**
  The device never sends the test voltage in any `ACCEL_*` line, so a wrongly
  captured voltage cannot be recovered from `raw_lines` afterwards. `accel_tests`
  row 1 (2026-08-08, pre-fix) is stuck at 1500 mV. Raw lines protect against
  *our parser* being wrong, not against a field that was never transmitted — do
  not answer "we can re-derive it later" for anything the device does not send.

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
- **The frontend is a single file** (`app/mbc2-dashboard.html`). Do not split it into multiple files.
- **Serial belongs in Python, not the browser.** All port access goes through `SerialManager` in `app/server.py` using `pyserial`. Do not reintroduce the Web Serial API or add a Node.js serial layer.
- **Two entry points, and they must stay in sync.** `app/app.py` (packaged, native window) and `app/server.py` (source/Mac, browser). Startup logic — port-conflict handling, `_prepare()`, shutdown — lives in `server.py` so both paths share it. Don't fork that logic into `app.py`.
- **Serial baud rate is 115200.** Do not change this.
- **The CH340 driver required is v3.9.2024.9** (ARM64). Newer versions dropped ARM64 support. Do not reference or suggest driver upgrades.
- **`API` in the frontend must stay relative (`''`).** It was
  `http://localhost:8766` while the page is served from `127.0.0.1:8766` — a
  different origin, so every call took a CORS preflight and `navigator.sendBeacon`
  (which cannot preflight) was silently dropped, meaning connection records were
  never closed on tab close. Making it absolute again re-breaks that.
- **`PROBE_TIMEOUT` (0.35 s) is deliberately short.** On this machine a
  connection to a *closed* loopback port takes ~2 s to be refused, so long
  timeouts cost ~3 s of every launch. A real listener accepts in ~2 ms, so the
  short timeout cannot produce a false "port free". Raising it undoes the fix.
- **`appRunCheckDeadline()` in `parseCSVTelemetry` is not redundant with the
  step timer — do not remove it.** Program step timing is wall-clock
  (`appRun.endsAt`); the `setTimeout` in `appRunSchedule` is only the primary
  path. Browsers throttle timers in a hidden window, and that timer is what
  ends a step, so relying on it alone runs the motor past the programmed time.
  SSE telemetry is not throttled, which is why the check rides on the data
  path. `appRunAdvancing` guards the several routes that can now end a phase.
  Covered by `node tests/test_program_timing.js` — run it after touching the
  runner. Node is a dev tool only; nothing in the app depends on it.
- **The Mac package is source + browser, not a `.app`.** `mac\BUILD MAC PACKAGE`
  stages `app/` beside a `.command` launcher and zips it. There is no
  PyInstaller, no pywebview, no `.icns`, no App Transport Security plist and no
  Gatekeeper notarization on that path — most macOS packaging advice found
  elsewhere is about a frozen `.app` and does not apply here.
- **Never build the Mac zip with `Compress-Archive` or `tar.exe`.** The first
  writes backslash path separators (spec-violating; macOS may extract the tree
  as flat files named `MBC2Dashboard\app\server.py`, and the shipped v4.0.1 zip
  had exactly this). The second pads past the end-of-central-directory record,
  so strict readers refuse to open the file at all. Use
  `mac\make-mac-zip.ps1`, which also sets the launcher's Unix execute bit and
  self-checks. Both failures are invisible on Windows.
- **Unload warnings must not rely on `beforeunload`.** WebView2 ignores it
  entirely, so the packaged app got no prompt and silently discarded unsaved
  rows. The close confirmation is a native pywebview dialog driven by recording
  state the frontend POSTs to `/api/recording/state`.

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
- **Writing a slot depends on that.** Settings → Program Sync → ⬆ Write to
  Device writes an app-library program into a slot with `SET_PROG`. It must
  never send `SAVE`, and must keep telling the user the slot is changed in RAM
  only. (The old Push & Run button in Device Control, which wrote a slot and
  immediately started it, has been removed — running is app-driven now.)
- **Program numbers are 1–50 only.** Program No.0 (MANU) cannot be read or written via `GET_PROG`/`SET_PROG`. Always validate before sending.

### Domain rules

- **Correct break-in direction for all Mini 4WD chassis is `R` (Reverse).** This applies to FM-A, Super-FM, MA, MS, and all other Tamiya chassis. `N` (Normal) is not used for racing break-in.
- **The Christchurch club break-in programs (PMPE, SPRF) are private club knowledge.** They must NEVER be included in `default_programs.json` or any seed data shipped with the app. They are distributed only as a separate importable `christchurch_protocol.json`.
- **Motor identifiers follow the format `MODEL-DIRECTION-NUMBER`** (e.g. `SD-R-01`). Sequential numbering resets per model code.

### API route ordering

- Routes are matched by an if-chain in `motor_api.py`'s `handle_motor_api()` — specific routes must be checked **before** generic catch-all routes.
- The generic `GET /api/motors/<identifier>` must come **after** routes like `/api/motors/roster`.
- Violating this causes the generic handler to intercept specific routes (e.g. treating `roster` as a motor identifier).

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
