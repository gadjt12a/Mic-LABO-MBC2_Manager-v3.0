# MBC2 Dashboard — Database Schema Reference

**Database:** SQLite (`mbc2.db`)  
**Current schema version:** v3.2

---

## Migration rules — mandatory

- **Always `CREATE TABLE IF NOT EXISTS`** — never bare `CREATE TABLE`
- **Always use `_add_column_if_missing(conn, table, column, type)`** before referencing any column that may not exist in older databases
- **Never drop or rename columns** — only add new ones
- Schema migration runs automatically on app launch
- The app must start cleanly against a fresh DB and against any existing v3.0+ database

---

## Tables

### `motors`

Motor registry. One row per physical motor.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `identifier` | TEXT UNIQUE | Format: `MODEL-DIRECTION-NUMBER` e.g. `SD-R-01` |
| `model_code` | TEXT | e.g. `SD` (Sprint Dash) |
| `direction` | TEXT | `R` or `N` (always `R` for racing) |
| `number` | INTEGER | Sequential per model code |
| `label` | TEXT | Human-readable label |
| `created_at` | TEXT | ISO8601 timestamp |
| `notes` | TEXT | Free text |

### `connections`

Device connection lifecycle. One row per USB connect event.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `connected_at` | TEXT | ISO8601 timestamp |
| `disconnected_at` | TEXT | ISO8601 timestamp, nullable |
| `end_reason` | TEXT | e.g. `user_disconnect`, `crash`, `timeout` |
| `port` | TEXT | COM port name |

### `sessions`

One row per break-in run (START→STOP or crash).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `connection_id` | INTEGER FK | → `connections.id` |
| `motor_identifier` | TEXT | → `motors.identifier` |
| `program_name` | TEXT | 4-char program name from device |
| `program_no` | INTEGER | Program number (0=MANU) |
| `started_at` | TEXT | ISO8601 timestamp |
| `ended_at` | TEXT | ISO8601 timestamp, nullable |
| `duration_sec` | INTEGER | Computed on session close |
| `end_reason` | TEXT | `completed`, `stopped`, `crashed`, `watchdog` |
| `loop_number` | INTEGER | Current loop/round at session end |
| `max_loop` | INTEGER | Total loops configured |
| `prog_loop` | INTEGER | Program loop counter |
| `prog_max_loop` | INTEGER | Program max loop |

### `session_data`

Raw telemetry rows. One row per CSV line received from device.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `session_id` | INTEGER FK | → `sessions.id` |
| `timestamp` | TEXT | ISO8601 timestamp (JS client time) |
| `program_no` | INTEGER | col[0] |
| `program_name` | TEXT | col[1] |
| `target_rpm` | INTEGER | col[2] — actual RPM value |
| `current_cycle` | INTEGER | col[3] |
| `max_cycle` | INTEGER | col[4] |
| `current_step` | INTEGER | col[5] |
| `run_state` | INTEGER | col[6] — see SERIAL_SPEC.md |
| `current_rpm` | INTEGER | col[7] — actual RPM value |
| `max_rpm` | INTEGER | col[8] — actual RPM value |
| `kv` | INTEGER | col[9] |
| `voltage_mv` | INTEGER | col[10] — mV |
| `set_voltage_mv` | INTEGER | col[11] — mV |
| `direction` | INTEGER | col[12] — 0–4 encoding |
| `current_ma` | INTEGER | col[13] — mA, smoothed |
| `elapsed_sec` | INTEGER | col[14] |
| `set_runtime_sec` | INTEGER | col[15] |
| `cool_elapsed_sec` | INTEGER | col[16] |
| `cool_set_sec` | INTEGER | col[17] |
| `temperature` | INTEGER | col[18] — °C |
| `total_rotations` | REAL | col[19] — cumulative rotation count (NOT charge) |
| `loop_number` | INTEGER | Loop/round number at time of row |
| `max_loop` | INTEGER | Total loops configured |
| `prog_loop` | INTEGER | Program loop counter |
| `prog_max_loop` | INTEGER | Program max loop |

### `connections`

USB serial connection lifecycle tracking. One row per connect event.

| Column | Type | Notes |
|---|---|---|
| `connection_id` | INTEGER PK | Auto-increment |
| `started_at` | TEXT | ISO8601 timestamp |
| `ended_at` | TEXT | ISO8601 timestamp, nullable if still open or crashed |
| `end_reason` | TEXT | `normal`, `crash`, `unknown` |
| `total_sessions` | INTEGER | Count of sessions completed during connection |
| `notes` | TEXT | Free text |

### `crash_events`

Motor state snapshots on unexpected silence (watchdog trigger) or detected crash.

| Column | Type | Notes |
|---|---|---|
| `event_id` | INTEGER PK | Auto-increment |
| `logged_at` | TEXT | ISO8601 timestamp |
| `connection_id` | INTEGER FK | → `connections.connection_id` |
| `connection_age_sec` | INTEGER | Seconds port was open before silence |
| `session_id` | INTEGER FK | → `sessions.id`, nullable |
| `session_age_sec` | INTEGER | Seconds since recording started |
| `rows_captured` | INTEGER | Rows in session buffer at time of event |
| `prog_name` | TEXT | 4-char program name at time of event |
| `prog_step` | INTEGER | Step number at time of event |
| `last_volts` | REAL | Last known voltage (V) |
| `last_amps` | REAL | Last known current (A) |
| `last_rpm` | INTEGER | Last known RPM |
| `last_kv` | INTEGER | Last known kV efficiency |
| `last_temp` | REAL | Last known temp (°C) |
| `motor_id` | INTEGER FK | → `motors.motor_id`, nullable |
| `motor_identifier` | TEXT | Denormalised motor identifier for display |
| `silence_duration_sec` | INTEGER | Seconds of no data before event fired |
| `trigger` | TEXT | `silence`, `disconnect`, `manual` |
| `notes` | TEXT | Free text |

### `programs`

Saved break-in programs (local DB copy — separate from device EEPROM).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `name` | TEXT | Display name |
| `program_data` | TEXT | JSON blob — step definitions |
| `source` | TEXT | `user`, `import`, `device_sync` |
| `created_at` | TEXT | ISO8601 timestamp |
| `updated_at` | TEXT | ISO8601 timestamp |
| `is_public` | INTEGER | 0=private, 1=exportable. Default 0 |

> **Never seed `programs` with Christchurch club protocols (PMPE, SPRF).** These are private club knowledge distributed separately as `christchurch_protocol.json`.

---

## Migration helper pattern

```python
def _add_column_if_missing(conn, table, column, col_type):
    cursor = conn.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cursor.fetchall()]
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()
```

Call this in the startup migration block for every column added after the initial table creation. Example:

```python
def migrate_db(conn):
    # v3.1 additions
    _add_column_if_missing(conn, 'sessions', 'connection_id', 'INTEGER')
    _add_column_if_missing(conn, 'sessions', 'duration_sec', 'INTEGER')
    _add_column_if_missing(conn, 'sessions', 'end_reason', 'TEXT')
    # v3.2 additions
    _add_column_if_missing(conn, 'session_data', 'loop_number', 'INTEGER')
    _add_column_if_missing(conn, 'session_data', 'max_loop', 'INTEGER')
    # etc.
```

---

## Key queries

### Get sessions for a motor
```sql
SELECT s.*, c.connected_at, c.port
FROM sessions s
LEFT JOIN connections c ON s.connection_id = c.id
WHERE s.motor_identifier = ?
ORDER BY s.started_at DESC;
```

### Get telemetry for a session
```sql
SELECT * FROM session_data
WHERE session_id = ?
ORDER BY timestamp ASC;
```

### Get crash events with session context
```sql
SELECT ce.*, s.motor_identifier, s.program_name
FROM crash_events ce
JOIN sessions s ON ce.session_id = s.id
ORDER BY ce.timestamp DESC;
```
