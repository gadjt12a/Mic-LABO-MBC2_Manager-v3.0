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

⚠ **Superseded 2026-08-07 by Phase 8** — see below. Push & Run was built on the
assumption that only device slots can run, which is not how this tool is meant
to work, and it never functioned against hardware.

---

## Phase 8 — App-driven program runner ✓ COMPLETE (2026-08-07)

The first hardware test of Push & Run revealed the model was wrong. The app is
the program engine: selecting a library program and pressing START PROG makes
the app walk the steps over serial. Device slots are for standalone running and
for importing programs built elsewhere — an alternative input, not the run path.

- [x] `startAppProgram()` and the `appRun` state machine: per step `START`,
      `SET_DIRECTION`, `SET_VOLTAGE`, hold for the run time, `STOP` and wait for
      any cool time, repeat for the cycle count.
- [x] STOP / PAUSE / NEXT act on whichever run is active. PAUSE stops the motor
      and freezes the clock; RESUME re-applies the step; NEXT skips the rest of
      the step and its cool.
- [x] `START` is sent only when the motor is not already turning; a direction
      change stops it first rather than reversing at speed.
- [x] Recording treats an app-driven run as a program run — the device reports
      `MANU` throughout and 0V during cool, either of which previously stalled
      recording or tripped the auto-stop. Rows carry the program label, cycle
      and step from the runner.
- [x] Push & Run removed from Device Control; writing a slot stays in
      Settings → Program Sync.
- [x] ⟳ ALL reads all 50 slots (no `GET_PROG:ALL` exists); empty slots hidden.
- [x] 💾 Save to Library turns a slot read off a device into a stored profile.
- [x] Baseline 3.0V restored to the program dropdown and redefined as a single
      3-minute 3.0V R step; it now runs app-driven like anything else.

Five defects found by hardware, none visible without it:

1. `get_all_profiles()` returned programs with **no steps**, so every library
   program loaded empty and any conversion produced a step-less program.
2. The program dropdown wrote **string** ids while the library holds numbers,
   and every lookup uses `===` — selecting a program matched nothing.
3. `SET_VOLTAGE` before `START` is ignored (SERIAL_SPEC 3-2 "valid during run").
4. `START` per step restarted the motor and reset the device log.
5. Two builders wrote the program dropdown; the one without the Baseline entry
   overwrote the one with it, making benchmark mode unreachable — which is why
   the `benchmarks` table had never held a single row.

---

## Firmware v0.200(Beta) — evaluated 2026-08-08, not yet installed

Compared the v0.110 and v0.200 images from `esp32.miclabo.xyz` by extracting
and diffing their strings. **There is no published spec for v0.200** — the
mic-LABO document covers v0.110 only, the manual directory has no other file,
and nothing exists publicly. Everything below is inferred from token names, not
from documentation or observed behaviour.

New in v0.200, absent from v0.110 (verified by byte count, 0 vs n occurrences):

| Area | Tokens |
|---|---|
| Accel test | `ACCEL_META,` `ACCEL_LOAD,` `ACCEL_CP,` `ACCEL_DONE,` `ACCEL_STALL,` `ACCEL_CK,` / `ACCEL_CK,FAIL` `ACCEL_ABORT` / `ACCEL_ABORT,NORPM` `ACCEL_SPIN2,STOPPED` |
| Stall test | `STALL_HEAD,duty,volt_mv,current_ma,pulses,i_early,i_late` then rows, `STALL_STOP,{ERR\|CURRENT\|ROTATED\|IDROP,n}`, `STALL_END` |
| Calibration | `GET_CALIB` / `SET_CALIB` → `CALIB:norm_volt:` `CALIB:rev_volt:` `CALIB:current:` `CALIB:temp:`, ACK `STATUS:OK:SET_CALIB:` |
| WiFi | `GET_WIFI` / `SET_WIFI:` → `WIFI:STATUS:` `WIFI:IP:` `WIFI:RSSI:`, `STATUS:OK:WIFI_CONNECTING` |

Device menus gain `AccelTest`, `Motor Test`, `Retry Accel Test?`. `BattEmulate`
already existed in v0.110.

The stall block is the interesting one: per-pulse duty, voltage, current and
early/late current samples is a far richer motor signature than the periodic
CSV, and nothing in v0.110 can produce it.

**Compatibility:** every v0.110 protocol token is still present in v0.200 —
same 10 setting keys, same `STATUS:`/`PROG:`/`LOG:` vocabulary, no removals. The
app should keep working unchanged.

**Unknown and unknowable from strings:** whether the periodic CSV columns
changed. Those are numeric and leave no strings, and every parsed field in the
database depends on them.

When the update is done:
- [ ] Capture raw serial and confirm the CSV is still 20 columns in the same order **before** trusting any session recorded on v0.200.
- [ ] Capture a full AccelTest and stall run raw, and derive the format from the data.
- [ ] `GET_CALIB` and record the values. **Do not send `SET_CALIB`** until its units are known — writing calibration blind corrupts every measurement the device makes.
- [ ] Only then ask Michihiro, with specific questions the data could not answer.

Rollback is available: `versions.csv` still lists v0.103–v0.110 and the device
has an OTA version picker.

---

## Phase 9 — Capture AccelTest results (proposed)

Verified on hardware 2026-08-08. AccelTest reports **the RPM a motor reaches at
three fixed current draws** (~750 / ~830 / ~2150 mA), per direction, in about 90
seconds per pass. Because the loads are fixed *currents*, results are directly
comparable between motors in a way peak RPM never was: same electrical input,
different mechanical output. See the appendix in `docs/SERIAL_SPEC.md`.

Why this is worth building. Six runs, three motors, two voltages each — first
pass of each shown:

| Motor | 3.0V No → Hi | lost | 4.0V No → Hi | lost |
|---|---|---|---|---|
| Box stock 1 | 19,080 → 8,970 | **−53%** | 24,060 → 15,125 | **−37%** |
| Box stock 2 | 16,560 → 9,058 | **−45%** | 20,540 → 14,320 | **−30%** |
| Torque-Tuned 2 | 18,630 → 14,664 | **−21%** | 23,400 → 19,905 | **−15%** |

The TT2 and box stock 1 have nearly the same free-running speed — 18,630 vs
19,080 at 3.0V, and 23,400 vs 24,060 at 4.0V — and the TT2 is **32-63% faster
under load**. Peak RPM, the only figure the app records today, cannot tell these
two motors apart at all.

**Load retention** (high-load ÷ no-load) reduces this to one comparable number:
box stock 47-70%, TT2 79-85%. Worth showing per motor per voltage.

**Constraints this data imposes on the design:**

1. **Current targets are per motor**, and vary widely by type — the TT2's
   no-load level was 313 mA against box stock's 749 mA, less than half. Store
   the actual currents: otherwise a 313 mA measurement gets compared against a
   749 mA one and both get called "no-load".
2. **Compare voltage-matched only.** Every figure, including load retention,
   changes with test voltage. Two *closely matched* motors even swapped places
   under load between 3.0V and 4.0V (stock 1 vs stock 2). Genuinely different
   motors did not — the TT2 won at both — so this is a caution about
   near-identical motors, not a general instability.

**Constraint that shapes the design: the app cannot start an AccelTest.** No
serial command exists for it; the test is started on the device. So every step
below is passive — the app watches for `ACCEL_*` lines and records what arrives.

### 9.1 Capture and store

- [ ] Recognise `ACCEL_CK` / `ACCEL_STALL` / `ACCEL_LOAD` / `ACCEL_DONE` in
      `parseLine()`. They are not CSV and must not reach the telemetry parser.
- [ ] New `accel_tests` table: motor_id, connection_id, started_at, test_voltage
      (from CSV `col11` during the run), per direction the three RPMs and three
      currents, plus the undecoded fields.
- [ ] **Store the raw lines verbatim** alongside the parsed values. The format is
      undocumented and partly undecoded — without the raw text a later insight
      cannot be applied retrospectively. (`session_data.raw_line` is empty for
      every row ever recorded; do not repeat that.)
- [ ] Attribute to the active motor, and warn — do not silently discard — if no
      motor is selected when a test completes.

### 9.2 Show it

- [ ] A result panel: No / Lo / Hi RPM per direction, with the test voltage.
- [ ] On the motor record, the history of its AccelTests.

### 9.3 Use it

- [ ] Compare motors at the same load rather than on peak RPM, voltage-matched.
- [ ] **Load retention** (high-load ÷ no-load) as a single headline figure — the
      one number that separated the TT2 from box stock while peak RPM could not.
- [ ] Pre/post break-in comparison: does break-in improve *loaded* RPM more than
      free RPM? This is answerable once a few motors have before/after tests, and
      is the first question this data makes askable.

### Open questions

- `f6` in `ACCEL_LOAD` — rises with voltage, inconsistent between passes, not kV.
- `ACCEL_STALL` payload — five samples per pass, fields undecoded.
- `STALL_HEAD,duty,volt_mv,current_ma,pulses,i_early,i_late` exists in firmware
  but neither run produced it. Find what triggers it; per-pulse data would be
  richer still.
- ~~Whether the current targets are fixed constants or vary by motor/voltage.~~
  **Answered:** constant across voltage within a motor, but 5–12% different
  between two motors. Store the actual values.
- ~~Whether a different type of motor still produces comparable load levels.~~
  **Answered:** no. A Torque-Tuned 2 used 313 mA where box stock used 749 mA at
  the "no-load" level. Load levels track the motor, so the actual currents must
  be stored and shown alongside any RPM figure.

Ask Michihiro only what the data cannot answer, and only after more runs.

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
