# MBC2 Dashboard — Version History

## v3.2 (current)

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
