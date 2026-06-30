# MBC2 Dashboard — Feature Roadmap

## Implementation priority order

Work through these in sequence. Do not jump ahead — each builds on the previous.

---

## Phase 1 — Parser hardening ✓ COMPLETE

**Goal:** Make the serial parser robust before adding any new commands.

- [x] Ignore `Debug:` prefixed lines (firmware emits these; will be removed in future firmware)
- [x] Handle expanded `run_state` values: `1=Paused`, `3=Overheat`, `5=Finished`, `90=Over Current`, `226=INA226 error`
- [x] Handle async `STATUS:COOLING` notification (device-initiated, no command)
- [x] Handle async `STATUS:LOW_AMP_LIMIT` notification
- [x] Route incoming lines by prefix: `STATUS:` / `PROG:` / `SETTING:` / `LOG:` / CSV / ignore

**Acceptance:** Parser handles all known line types without throwing errors or storing garbage.

**Completed in v3.3** — Parser now routes all line types, STATUS handlers process ACKs/errors/async notifications, run_state tracked in UI state.

---

## Phase 2 — Manual Run panel ✓ COMPLETE

**Goal:** Basic bidirectional control from the dashboard.

Controls to expose:
- [x] `START` (MANU mode)
- [x] `START_PROG:n` (launch saved program by number)
- [x] `STOP`
- [x] `PAUSE` / `RESUME` (with state awareness — show correct button for current state)
- [x] `NEXT_STEP` (with confirmation prompt — this is destructive to the current step)
- [x] `SET_VOLTAGE:v` (with ACK feedback — display actual applied voltage from response)
- [x] `SET_CURRENT_LIMIT:a` (with ACK feedback — display actual applied limit from response; 0=OFF)
- [x] `SET_DIRECTION:R/N` (default R, rarely changed)

**UI rules:**
- [x] PAUSE and RESUME are mutually exclusive — show only the relevant one based on `run_state` from CSV stream
- [x] NEXT_STEP must have a confirmation step — it cannot be undone
- [x] Display the ACK-confirmed voltage and current limit, not the requested values
- [x] `SET_DIRECTION:N` should be visually de-emphasised (R is correct for all racing use)

**Acceptance:** Can start, pause, resume, stop a run and adjust voltage/current from the browser.

**Completed in v3.3** — Device Control panel added to right sidebar with all controls.

---

## Phase 3 — GET_LOG integration

**Goal:** Retrieve end-of-run summary from device and store in DB.

- Send `GET_LOG` automatically after `STATUS:STOPPED` is received
- Parse `LOG:HEAD`, `LOG:STEP`, `LOG:CYC`, `LOG:END` response
- Store summary alongside the session record
- Display per-step summary in session detail view

**Note on units:** `LOG:STEP` voltage field is internal × 0.1V — different to CSV stream mV. Convert correctly.

**Acceptance:** After a run ends, session detail view shows per-step RPM, current, temp summary from device log.

---

## Phase 4 — START_PROG:n (launch saved programs)

**Goal:** Launch a specific saved program from the dashboard.

- List saved programs (from local DB) with their number
- Allow user to select and launch with `START_PROG:n`
- Handle `STATUS:ERR:PROG_NO` gracefully

**Acceptance:** Can select and start a named program from the dashboard UI.

---

## Phase 5 — Program sync (GET_PROG / SET_PROG)

**Goal:** Read and write programs on the device from the dashboard.

- `GET_PROG:n` — read a program from device into local DB
- `SET_PROG:n` — push a local program to device RAM
- Display encoding/decoding correctly (time index, char table, voltage × 0.1V)
- `SAVE` button — explicit user action only, with warning about EEPROM write cycles

**Encoding requirements:**
- Program name: integer array 0–36 ↔ ASCII character table
- Voltage: internal × 0.1V ↔ float V
- Time: non-linear index table (see SERIAL_SPEC.md §Encodings)
- Direction: integer 0–4 ↔ label

**Rules:**
- `SET_PROG` changes are RAM-only. Make this visible in the UI ("Not saved to device").
- `SAVE` must be a separate explicit button, never automatic.
- Warn user that `SAVE` writes EEPROM — should not be done repeatedly.

**Acceptance:** Can read a program from device, edit it in the dashboard, push it back, and optionally persist.

---

## Phase 6 — Device settings panel (GET_SETTING / SET_SETTING)

**Goal:** Read and write device system settings.

- `GET_SETTING:ALL` on connect to read current device config
- Display all settings with their human-readable labels and unit conversions
- Allow editing individual settings with `SET_SETTING:key:value`
- `SAVE` button (same rules as Phase 5 — explicit, warned, batched)

**Acceptance:** Can view and edit all device settings from the dashboard.

---

## Deferred / future

These are out of scope until the above phases are stable:

- **Program builder UI** — visual step editor for building programs from scratch
- **Export to device** — push a full program set to device and save in one workflow
- **Community program sharing** — import/export program JSON for sharing with other racers
- **Efficiency scoring** — weighted RPM scoring vs Tamiya spec and peer motors

---

## Out of scope permanently

- Multi-device support (single MBC2 per session by design)
- Non-Chrome browser support (Web Serial API is Chrome-only by design)
- Automatic `SAVE` of any kind
- Inclusion of Christchurch club protocols (PMPE, SPRF) in any shipped seed data
