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

> **Verified against `app/schema.sql` and a live database on 2026-08-09.**
> Several tables below previously documented a design that was never built —
> `sessions` was listed with `connection_id`, `started_at`, `duration_sec` and
> `end_reason`, none of which exist, and the example queries could not have run.
> If a column here is not in `schema.sql`, treat this file as wrong and fix it.

### `motors`

Motor registry. One row per physical motor.

| Column | Type | Notes |
|---|---|---|
| `motor_id` | INTEGER PK | Auto-increment |
| `identifier` | TEXT UNIQUE | Format `MODEL-DIRECTION-NUMBER`, e.g. `SD-R-01` |
| `model_id` | INTEGER FK | → `motor_models.model_id` |
| `breakin_direction` | TEXT | `F` or `R` — **always `R` for racing break-in** |
| `date_registered` | TEXT | `date('now')` default |
| `status` | TEXT | `Active`, `Retired`, `Lost`, `Damaged` |
| `notes` | TEXT | Free text |

The model code, direction and sequence number are **not** stored as separate
columns — they are parsed out of `identifier` where needed.

### `motor_models`, `mount_types`, `chassis`, `motor_chassis_assignments`

Reference data seeded on first launch, plus the motor↔chassis join.

| Table | Key columns |
|---|---|
| `motor_models` | `model_id`, `name`, `code`, `shaft_type`, `speed_stars`, `torque_stars`, `legal_classes`, `notes` |
| `mount_types` | `mount_type_id`, `name`, `shaft_type`, `default_direction` |
| `chassis` | `chassis_id`, `name`, `mount_type_id`, `notes` |
| `motor_chassis_assignments` | `assignment_id`, `motor_id`, `chassis_id` |

### `profiles`, `programs`, `program_steps`

The app's own program library, three levels deep: a profile holds programs, a
program holds steps. This is **not** the device's 50 slots — see `CLAUDE.md` on
why the two are not interchangeable.

| Table | Key columns |
|---|---|
| `profiles` | `profile_id`, `name`, `motor_model`, `chassis`, `class`, `notes`, `created_date`, `modified_date` |
| `programs` | `program_id`, `profile_id` FK, `name`, `mbc2_label` (4-char device label), `step_order`, `cycles`, `target_rpm`, `notes` |
| `program_steps` | `step_id`, `program_id` FK, `step_order`, `volts`, `direction` (`F`/`R`/`N`), `duration_sec`, `cool_sec` (NULL = full cool), `notes` |

> **Never seed these with Christchurch club protocols (PMPE, SPRF).** They are
> private club knowledge, distributed separately as `christchurch_protocol.json`.

### `sessions`

One row per recorded run. Deliberately thin — the detail lives in
`session_data`, and the run's end state is not summarised here.

| Column | Type | Notes |
|---|---|---|
| `session_id` | INTEGER PK | Auto-increment |
| `motor_id` | INTEGER FK | → `motors.motor_id`, NOT NULL |
| `session_type` | TEXT | `Benchmark`, `Breakin`, `Manual` |
| `session_date` | TEXT | `datetime('now')` default |
| `notes` | TEXT | Free text |
| `ambient_temp_c` | REAL | Optional room temp |

> **There is no `connection_id` on `sessions`.** Sessions are not linked to the
> connection they happened on, which is why `connections.total_sessions` is 0 on
> every row ever written. Joining sessions to connections requires comparing
> timestamps. Wiring this up properly is an open item, not a bug to be assumed
> already done.

### `session_data`

Telemetry rows. One row per CSV line kept — a **parsed subset**, not all 20
columns of the wire format. For the full CSV layout see
[`SERIAL_SPEC.md`](SERIAL_SPEC.md).

| Column | Type | Notes |
|---|---|---|
| `data_id` | INTEGER PK | Auto-increment |
| `session_id` | INTEGER FK | → `sessions.session_id` |
| `timestamp_ms` | INTEGER | **ms since session start**, not a clock time |
| `raw_line` | TEXT | The original CSV line — see the warning below |
| `mode` | TEXT | `MANU`, `PROG`, … |
| `program_step` | INTEGER | |
| `voltage_mv` | INTEGER | mV |
| `current_ma` | INTEGER | mA (col[13], already smoothed by firmware) |
| `rpm` | INTEGER | col[7], already an actual RPM value |
| `temp_c` | REAL | °C |
| `elapsed_sec` | INTEGER | |
| `rpm_cap` | INTEGER | |
| `kv_efficiency` | REAL | Calculated — RPM per volt |

> ⚠ **`raw_line` is empty for every row ever written.** The column exists and
> nothing populates it, so an insight that needs an unparsed field cannot be
> applied retrospectively to existing sessions. This is the specific mistake the
> AccelTest tables were designed to avoid.

### `benchmarks`

Summary row for a benchmark run. Benchmarks store **summary only — no telemetry
rows** (by design; the charts show a dashed trace and a disclosure for them).

`benchmark_id`, `session_id` FK, `motor_id` FK, `benchmark_type`
(`Pre`/`Post`/`Periodic`), `voltage_v`, `direction`, `duration_sec`,
`peak_rpm`, `avg_rpm`, `peak_current_ma`, `avg_current_ma`, `peak_temp_c`,
`final_temp_c`, `notes`.

### `motor_breakin_log`

Which program was run on which motor and when: `log_id`, `motor_id`,
`program_id`, `date_run`, `session_id`, `notes`.

### `connections`

USB serial connection lifecycle. One row per connect event.

| Column | Type | Notes |
|---|---|---|
| `connection_id` | INTEGER PK | Auto-increment |
| `started_at` | TEXT | ISO8601 timestamp |
| `ended_at` | TEXT | ISO8601, nullable if still open or crashed |
| `end_reason` | TEXT | `normal`, `window_closed`, `tab_closed`, `app_closed`, `crash`, `unknown` |
| `total_sessions` | INTEGER | **Always 0** — see the `sessions` note above |
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

### `accel_tests`

One completed AccelTest (firmware v0.200+). The test is started **on the device** —
there is no serial command for it — so these rows are written from whatever
`ACCEL_*` lines arrive.

| Column | Type | Notes |
|---|---|---|
| `accel_test_id` | INTEGER PK | Auto-increment |
| `recorded_at` | TEXT | `datetime('now')` default |
| `motor_id` | INTEGER FK → `motors` | **Nullable** — a test with no motor selected is saved unattributed, not discarded |
| `motor_identifier` | TEXT | Denormalised copy, for display when the motor is deleted |
| `connection_id` | INTEGER FK → `connections` | |
| `test_voltage_mv` | INTEGER | From CSV `col11`, sampled from *before* the test starts — `col11` reads 0 while the device drives the load ramp |
| `pass_count` | INTEGER | |
| `firmware` | TEXT | |
| `raw_lines` | TEXT | Every `ACCEL_*` line verbatim, newline-joined |
| `notes` | TEXT | |

### `accel_test_passes`

One row per pass. A test runs 1–10 passes (device setting), and "both directions"
produces one pass each way.

| Column | Type | Notes |
|---|---|---|
| `accel_pass_id` | INTEGER PK | Auto-increment |
| `accel_test_id` | INTEGER FK → `accel_tests` | |
| `pass_no` | INTEGER | |
| `direction` | TEXT | `N` or `R` |
| `no_rpm` / `no_ma` | INTEGER | No-load level |
| `lo_rpm` / `lo_ma` | INTEGER | Low-load level |
| `hi_rpm` / `hi_ma` | INTEGER | High-load level |
| `field5` | INTEGER | Undecoded — probably winding resistance in mΩ |
| `field6` | INTEGER | Undecoded. Rises with voltage, inconsistent between passes, not kV |
| `raw_line` | TEXT | The `ACCEL_LOAD` line verbatim |

> **The currents are not optional.** The device derives the three load levels
> *per motor*, so "no load" is a different current on different motors — a
> Torque-Tuned 2 drew 313 mA where a box stock drew 749 mA. Without `*_ma`,
> two motors measured at very different loads both read as "no-load" and the
> RPMs look comparable when they are not.

> Field names mirror what the device sends rather than what we think it means,
> and `raw_line`/`raw_lines` are stored so a later decode can be applied to
> tests already recorded. `session_data.raw_line` has been empty for every row
> ever written — that is the mistake being avoided here.

> ⚠ **`test_voltage_mv` is the one field the raw lines cannot rescue.** It does
> not come from the device at all — it is sampled from CSV `col11` before the
> test begins — so if it was captured wrongly it cannot be re-derived from
> `raw_lines` later. `accel_tests` row 1 (recorded 2026-08-08, before the fix)
> reads 1500 mV for a run believed to have been at 3.0 V, and that is now
> unrecoverable. Storing raw lines protects against our parser being wrong, not
> against a field the device never sent.

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

> The columns above are **illustrative and do not exist** — an earlier version of this example used `sessions.connection_id` / `duration_sec` / `end_reason`, which readers then took for real columns.
>
> As of 2026-08-09 `_add_column_if_missing()` is **defined in `db_manager.py` and never called**. Every table is created whole by `CREATE TABLE IF NOT EXISTS`, so no column has yet needed adding to an existing table. The helper is the required mechanism the first time one does — do not reach for a raw `ALTER TABLE`.

```python
def migrate_db(conn):
    _add_column_if_missing(conn, 'motors', 'retired_date', 'TEXT')
    _add_column_if_missing(conn, 'sessions', 'ambient_humidity', 'REAL')
```

---

## Key queries

All three below were run against a live database on 2026-08-09. The versions
previously here referenced `sessions.motor_identifier`, `sessions.started_at`,
`sessions.connection_id` and `session_data.timestamp` — none of which exist, so
none of them could ever have run.

### Sessions for a motor

```sql
SELECT s.session_id, s.session_type, s.session_date, s.notes
FROM sessions s
JOIN motors m ON m.motor_id = s.motor_id
WHERE m.identifier = ?
ORDER BY s.session_date DESC;
```

There is no join to `connections` — `sessions` has no `connection_id`.

### Telemetry for a session

```sql
SELECT * FROM session_data
WHERE session_id = ?
ORDER BY timestamp_ms ASC;
```

`timestamp_ms` is milliseconds since the session started, not a clock time.

### Crash events with motor context

```sql
SELECT ce.event_id, ce.logged_at, ce.trigger, ce.silence_duration_sec,
       ce.motor_identifier, ce.prog_name, ce.rows_captured
FROM crash_events ce
ORDER BY ce.logged_at DESC;
```

`crash_events` already carries `motor_identifier` and `prog_name` denormalised,
so the join to `sessions` the old version attempted is unnecessary — and
`ce.session_id` is frequently NULL anyway.

### AccelTest results for a motor, best load retention first

```sql
SELECT t.recorded_at, t.test_voltage_mv, p.direction,
       p.no_rpm, p.no_ma, p.hi_rpm, p.hi_ma,
       ROUND(100.0 * p.hi_rpm / p.no_rpm, 1) AS retention_pct
FROM accel_tests t
JOIN accel_test_passes p ON p.accel_test_id = t.accel_test_id
WHERE t.motor_id = ?
ORDER BY retention_pct DESC;
```

Only compare rows with the same `test_voltage_mv`.
