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

## Phase 3 — GET_LOG integration ✓ COMPLETE

**Goal:** Retrieve end-of-run summary from device and display in UI.

- [x] Send `GET_LOG` automatically after `STATUS:STOPPED` is received
- [x] Parse `LOG:HEAD`, `LOG:STEP`, `LOG:CYC`, `LOG:END` response
- [x] Display per-step summary in right panel (cycle, step, RPM, max RPM, voltage, current, temp)
- [ ] Store summary alongside the session record (deferred — requires schema migration)

**Note on units:** `LOG:STEP` voltage field is internal × 0.1V — different to CSV stream mV. Convert correctly.

**Acceptance:** After a run ends, Device Run Log panel shows per-step summary from device.

**Completed in v3.3** — GET_LOG sent on stop, parsed and displayed in UI. DB storage deferred.

---

## Phase 4 — START_PROG:n (launch saved programs) ✓ COMPLETE

**Goal:** Launch a specific saved program from the dashboard.

- [x] List saved programs (from local DB) with their number
- [x] Allow user to select and launch with `START_PROG:n`
- [x] Handle `STATUS:ERR:PROG_NO` gracefully

**Acceptance:** Can select and start a named program from the dashboard UI.

**Completed in v3.4.2** — START PROGRAM section replaced with a dropdown populated from `devicePrograms` cache. Programs synced via Settings → Program Sync appear as `[n] NAME`. `STATUS:ERR:PROG_NO` handled by existing error handler.

---

## Phase 5 — Program sync (GET_PROG / SET_PROG) ✓ COMPLETE

**Goal:** Read and write programs on the device from the dashboard.

- [x] `GET_PROG:n` — read a program from device and decode
- [x] `SET_PROG:n` — push a program to device RAM
- [x] Display encoding/decoding correctly (time index, char table, voltage × 0.1V)
- [x] `SAVE` button — explicit user action only, with warning about EEPROM write cycles

**Encoding requirements:**
- [x] Program name: integer array 0–36 ↔ ASCII character table
- [x] Voltage: internal × 0.1V ↔ float V
- [x] Time: non-linear index table (see SERIAL_SPEC.md §Encodings)
- [x] Direction: integer 0–4 ↔ label

**Rules:**
- [x] `SET_PROG` changes are RAM-only. Toast indicates "not saved".
- [x] `SAVE` must be a separate explicit button, never automatic.
- [x] Warn user that `SAVE` writes EEPROM — confirmation dialog.

**Acceptance:** Can read a program from device, view it in the dashboard, push it back, and optionally persist.

**Completed in v3.3** — Program sync UI added with READ/WRITE/SAVE buttons. Full encode/decode for all fields.

---

## Phase 6 — Device settings panel (GET_SETTING / SET_SETTING) ✓ COMPLETE

**Goal:** Read and write device system settings.

- [x] `GET_SETTING:ALL` — read all 10 settings from device
- [x] Display all settings with human-readable labels and unit conversions
- [x] Allow editing individual settings with `SET_SETTING:key:value`
- [x] `SAVE` button (same rules as Phase 5 — explicit, warned, batched)

**Settings supported:**
- overheat (°C), limit_volt (V), limit_current (A)
- brightness, measure_step, cheer_up (V)
- pulse_v (V), pulse_sec (s), pulse_pattern, buzzer_volume

**Acceptance:** Can view and edit all device settings from the dashboard.

**Completed in v3.3** — Settings panel with READ ALL, display, and editor modal. All unit conversions handled.

---

## Open issues

- **`session_data.raw_line` is always empty.** Cause found: `autoSaveSession`
  writes `raw_line: r.raw || ''`, but the row object built in the data handler
  never sets a `raw` field. Every parsed column is stored correctly, so no
  analysis depends on it. Decide whether to carry the original CSV line
  through into the row object, or stop writing the column (per the schema
  rules, never drop it).
- **Recording with no motor selected is allowed.** It warns at start and again
  at save, and the rows stay in memory for CSV export, but nothing reaches the
  database. Consider making it a blocking confirm rather than a toast.

## Phase 7 — Unified program controls ✓ COMPLETE (2026-08-07)

Raised by Kris 2026-08-06: the two program lists are different things and the
UI did not say so. The app library holds programs you *design*; the device
slots hold programs the hardware can actually *run*. Selecting an app program
and pressing start ran the motor in MANU, because nothing was sent to the
device.

- [x] Both lists moved into one `Break-in Program` section, labelled
      **In this app** and **On the device**.
- [x] `PAUSE` and `NEXT` moved there from Device Control — they act on a
      running program, not on a manual run. Device Control keeps START/STOP,
      voltage, current limit and direction.
- [x] **Push & Run** — `SET_PROG:n` the selected app program into a chosen
      slot, then `START_PROG:n`. RAM-only; `SAVE` is never sent. The confirm
      names the slot, names what currently occupies it, and states that the
      stored program returns after a power cycle. Slot validated 1–50 so
      slot 0 / MANU can never be written.
- [x] Helpers: `getSelectedAppProgram()`, `appProgramToDeviceProgram()`
      (library shape → `encodeProgram` shape), `programTimeToSeconds()`.

⚠ **Not yet exercised against hardware.** The conversion in
`appProgramToDeviceProgram()` is the part to check first if a pushed program
runs with wrong voltages or step timings.

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
- ~~Non-Chrome browser support~~ — no longer a restriction. v4.0 moved serial
  into Python, so the browser plays no part in device access. Windows packages
  run in their own window; from source, any modern browser works.
- Automatic `SAVE` of any kind
- Inclusion of Christchurch club protocols (PMPE, SPRF) in any shipped seed data
