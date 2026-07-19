# MBC2 Dashboard — Version History

## v3.4.1 (current)

- **Session save fix** — telemetry rows now persist; duplicate session records eliminated; CSV export no longer empty
- **Server hardening** — localhost-only bind, threaded request handling
- **Settings tab fix** — device program reads now display
- **Safety/UX** — tab-close warning, server health indicator, styled confirm dialogs, chart axis labels, UI scale control, device-driven voltage limit
- **Repo hygiene** — `mbc2.db` untracked from git; `*.db` ignored
- **Packaging** — `DEPLOYMENT_PLAN.md` drafted for v4 (installer / USB / Mac)

## v3.4

- **Connection tracking** — `connections` table records each USB serial connection lifecycle
- **Crash Log** — `crash_events` table captures full motor state on data silence
- **Silence watchdog** — auto-detects 30+ seconds of no serial data while recording
- **Crash Log tab** — view crash events with connection context and session history
- **Extras dropdown** — Raw Data and Crash Log tabs grouped under Extras menu
- **Code cleanup** — removed orphaned roster table functions and CSS

## v3.3

- **Phase 1: Parser hardening** — serial parser now routes lines by prefix
- Added handlers for `STATUS:`, `PROG:`, `SETTING:`, `LOG:` message types
- STATUS message handler processes ACKs, errors, and async notifications (`COOLING`, `LOW_AMP_LIMIT`)
- Added `run_state` tracking (Running, Paused, Cooling, Overheat, Finished, Over Current, INA226 Error)
- Added `sendCommand()` function for bidirectional communication
- Fixed raw data column labels (col[13] is current_ma, not col[19])
- Debug lines now properly ignored at parser entry point

- **Phase 2: Device Control panel** — bidirectional control from the dashboard
- START/STOP buttons for MANU mode
- START PROG button with program number selector (1-50)
- PAUSE/RESUME button (context-aware based on run_state)
- NEXT STEP button with confirmation dialog
- Voltage slider and input with ACK-confirmed value display
- Current limit input with SET button and ACK confirmation
- Direction toggle (R/N) with R visually emphasised
- Run state indicator showing device status

- **Phase 3: GET_LOG integration** — automatic run log retrieval
- GET_LOG sent automatically when device stops
- Parses LOG:HEAD, LOG:STEP, LOG:CYC, LOG:END responses
- Accumulates step data with proper unit conversions (RPM × 10, voltage × 0.1)
- Displays per-step summary table in right panel (cycle, step, RPM, max, V, mA, °C)
- Overheat steps highlighted in red

- **Phase 5: Program sync (GET_PROG / SET_PROG)** — read/write device programs
- READ button fetches program from device and decodes all fields
- WRITE button encodes and sends program to device RAM
- Full encoding/decoding for program names (char table 0-36)
- Non-linear time index conversion (0-77 → seconds)
- Voltage conversion (internal × 0.1V)
- Direction encoding (0-4 ↔ OFF/N/R/NP/RP)
- SAVE TO EEPROM button with confirmation warning
- Program display shows name, cycles, target RPM, and step table

- **Phase 6: Device settings panel (GET_SETTING / SET_SETTING)**
- READ ALL button fetches all 10 device settings
- Settings display with human-readable labels and unit conversions
- Settings editor modal for modifying values
- Per-setting SET buttons write individual settings to RAM
- Supports: overheat, limit_volt, limit_current, brightness, measure_step, cheer_up, pulse_v, pulse_sec, pulse_pattern, buzzer_volume

## v3.2

- Added connection lifecycle tracking: `connections` table, `connection_id` FK on sessions
- Added `duration_sec` and `end_reason` columns to `sessions`
- Crash Log tab now shows full session history per connection alongside crash snapshots
- Loop/round tracking: `loop_number`, `max_loop`, `prog_loop`, `prog_max_loop` captured in session data and crash events
- Schema auto-migrates via `CREATE TABLE IF NOT EXISTS` and `_add_column_if_missing` on launch

## v3.1

- Added crash/data-loss event logging
- `crash_events` table capturing full motor state snapshots
- JS silence watchdog: fires after 30 seconds of no data while recording
- Crash Log UI tab

## v3.0

- Major architectural shift: hybrid CSV+SQLite → fully DB-only storage
- Eliminated data loss from path resolution failures
- Eliminated fragile fuzzy timestamp CSV matching
- All session data written directly to SQLite

## Pre-v3.0

- Hybrid CSV + SQLite storage (deprecated)
- CSV files written to disk, SQLite used for metadata only
