# MBC2 Dashboard — Version History

## v3.3 (current)

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
