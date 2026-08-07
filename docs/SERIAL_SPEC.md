# MBC2 Serial Interface Specification

**Target firmware:** MBC2 v0.110+  
**MCU:** ESP32-WROOM-32  
**Source:** mic-LABO official spec (Michihiro Nakagawa), published 2026-06-30 —
[MBC2_serial_interface_spec.html](https://mic-labo.com/mbc2_manual/MBC2_serial_interface_spec.html)

> **v0.200(Beta) is not covered by this document, or by any published spec.**
> It adds serial commands and data streams that do not exist in v0.110 — see
> the appendix at the end of this file, and `docs/FEATURE_ROADMAP.md`.
>
> Verified against v0.200 on 2026-08-08: the **periodic CSV stream is
> unchanged** — still 20 columns in the same order. Settings, programs and the
> `STATUS:`/`PROG:`/`SETTING:`/`LOG:` vocabulary are also unchanged.

---

## Physical layer

| Setting | Value |
|---|---|
| Interface | UART via USB (CH340 USB-UART bridge) |
| Baud rate | 115200 |
| Format | 8N1 |
| Line ending (MBC2→PC) | `\r\n` |
| Line ending (PC→MBC2) | `\n` or `\r` (either accepted) |
| Encoding | ASCII throughout |
| Max command length | 200 characters (buffer discarded if exceeded) |

---

## MBC2→PC: Periodic CSV stream

Emitted approximately once per second while a program is running (`sendLog()`). No header row.

### Column definitions

| Col | Field | Type | Unit / Notes |
|---|---|---|---|
| 0 | `program_no` | int | Running program number. 0 = MANU |
| 1 | `program_name` | string | 4-char name (already ASCII-decoded by firmware) |
| 2 | `target_rpm` | int | Target RPM — **actual RPM value** (internal × 10). 0 = not set |
| 3 | `current_cycle` | int | Current cycle number (1-based) |
| 4 | `max_cycle` | int | Total cycle count |
| 5 | `current_step` | int | Current step number (1-based) |
| 6 | `run_state` | int | See run_state table below |
| 7 | `current_rpm` | int | Current RPM — **actual RPM value** (internal × 10). No further multiplication needed |
| 8 | `max_rpm` | int | Max RPM — actual RPM value (internal × 10) |

> **Do not divide col07/col08 by 10.** The official spec phrases these as
> "actual value × 10", which reads like the transmitted number needs dividing.
> It does not — the firmware has already done the multiplication, and the value
> on the wire is real RPM. Proof from a captured line:
> `…,0,19320,19680,6450,2995,3000,…` → 19320 ÷ 2.995 V = **6450**, exactly the
> kV the device reports in col09. Were the RPM 1,932 the kV would be 645.
> Getting this wrong silently divides every RPM and kV in the database by ten.
| 9 | `kv` | int | KV value (rpm/V). 0 when voltage is 0 |
| 10 | `voltage_mv` | int | Current voltage in mV. 1000 = 1.000V |
| 11 | `set_voltage_mv` | int | Set voltage in mV (run_setvolt × 100) |
| 12 | `direction` | int | Rotation direction — see direction encoding table |
| 13 | `current_ma` | int | Current in mA. **Exponential smoothing already applied by firmware.** Use directly. |
| 14 | `elapsed_sec` | int | Elapsed time in current step (seconds) |
| 15 | `set_runtime_sec` | int | Configured step duration (seconds) |
| 16 | `cool_elapsed_sec` | int | Cooling elapsed time (seconds) |
| 17 | `cool_set_sec` | int | Cooling configured duration (seconds) |
| 18 | `temperature` | int | Temperature (°C) |
| 19 | `total_rotations` | float | Cumulative rotation count (`log_rotate_total ÷ 1000`). **This is rotations, not charge.** |

### run_state values

| Value | State |
|---|---|
| 0 | Running |
| 1 | Paused |
| 2 | Cooling |
| 3 | Overheat stop |
| 5 | Finished |
| 90 | Over current stop |
| 226 | INA226 sensor error |

### CSV example

```
3,ABCD,15000,2,5,1,0,14230,15100,4922,2891,3000,2,982,47,120,0,30,28,12.453
```

---

## PC→MBC2: Commands

All commands are ASCII, terminated with `\n` (or `\r`).

### 3-1. Execution control

| Command | Action | Response |
|---|---|---|
| `START\n` | Start MANU mode (program No.0) | `STATUS:RUNNING` |
| `START_PROG:n\n` | Start break-in program n (1–50) | `STATUS:RUNNING` or `STATUS:ERR:PROG_NO` |
| `STOP\n` | Immediately stop, return to menu, save log | `STATUS:STOPPED` |
| `PAUSE\n` | Stop motor, freeze timer. Time does not advance until RESUME | `STATUS:OK:PAUSE` / `STATUS:ERR:NOT_RUNNING` / `STATUS:ERR:ALREADY_PAUSED` |
| `RESUME\n` | Resume from PAUSE. Timer continues from where it stopped | `STATUS:OK:RESUME` / `STATUS:ERR:NOT_PAUSED` |
| `NEXT_STEP\n` | Force-skip current step. Blocks until motor stops (may take seconds). On final step, completes program | `STATUS:OK:NEXT_STEP` / `STATUS:OK:NEXT_STEP:FINISHED` / `STATUS:ERR:NOT_RUNNING` |

### 3-2. Real-time settings (valid during run)

| Command | Action | Response |
|---|---|---|
| `SET_VOLTAGE:v\n` | Set voltage in V (e.g. `2.5`). Clamped to `limit_volt`. **ACK echoes actual applied value.** | `STATUS:OK:SET_VOLTAGE:v` |
| `SET_DIRECTION:R\n` | Set direction to Reverse | `STATUS:OK:SET_DIRECTION:R` |
| `SET_DIRECTION:N\n` | Set direction to Normal | `STATUS:OK:SET_DIRECTION:N` |
| `SET_CURRENT_LIMIT:a\n` | Set CC current limit in A. `0` = OFF. Clamped to `limit_current`. **ACK echoes actual applied value.** | `STATUS:OK:SET_CURRENT_LIMIT:a` |

> **Important:** `SET_VOLTAGE` and `SET_CURRENT_LIMIT` responses echo the **clamped actual value**, not what was requested. Always update state from the ACK, not the sent command.

> **"Valid during run" is literal** (confirmed on hardware 2026-08-07). These
> settings only take effect while the motor is running. `SET_VOLTAGE` sent
> before `START` is acknowledged but does nothing — the motor starts at 0V and
> you get the direction relay clicking with nothing turning. Always `START`
> first, then apply direction and voltage.
>
> Two consequences for anything that drives the device step by step:
> - `START` **restarts the run**. Sending it once per step stops and restarts
>   the motor at every boundary (rpm visibly drops to near zero) and resets the
>   device's internal log, so the `LOG:` dump on `STOP` describes only the final
>   step. Send `START` once, then change voltage on the fly.
> - `START` resumes at **whatever voltage the device last held**, which may be
>   far higher than the next step wants. Set the target voltage before `START`
>   as well — it is ignored while idle, but harmless — and again immediately
>   after, so a stale high voltage is never applied even briefly.

### 3-3. Program read/write (No.1–50 only)

| Command | Action | Response |
|---|---|---|
| `GET_PROG:n\n` | Read program n | `PROG:n,<27 values>` |
| `SET_PROG:n,<27 values>\n` | Write program n. **RAM only — not persisted until `SAVE`.** All 27 values required; any range violation = no change. | `STATUS:OK:SET_PROG:n` / `STATUS:ERR:*` |

> **No.0 (MANU) cannot be read or written.** Returns `STATUS:ERR:PROG_NO`.

#### PROG row format

```
PROG:n,name0,name1,name2,name3,cycle,rstop,target,v1,r1,t1,c1,v2,r2,t2,c2,v3,r3,t3,c3,v4,r4,t4,c4,v5,r5,t5,c5
```

| Field | Position | Range | Meaning |
|---|---|---|---|
| name0–3 | 0–3 | 0–36 | 4-char name (character table index — see §Encodings) |
| cycle | 4 | 1–99 | Cycle count |
| rstop | 5 | 0–250 | Rotation stop threshold. 0 = none. Threshold = value × 100 (internal pulse count) |
| target | 6 | 0–99 | Target RPM. 0 = none. Actual RPM = value × 1000 |
| v1–v5 | 7,11,15,19,23 | 0–90 | Step voltage. Actual V = value × 0.1 |
| r1–r5 | 8,12,16,20,24 | 0–4 | Step direction (direction encoding table) |
| t1–t5 | 9,13,17,21,25 | 0–77 | Step runtime (time index — see §Encodings) |
| c1–c5 | 10,14,18,22,26 | 0–77 | Step cooltime (time index — see §Encodings) |

### 3-4. System settings

| Command | Action | Response |
|---|---|---|
| `GET_SETTING:ALL\n` | Read all settings (10 lines) | `SETTING:key:value` × 10 |
| `GET_SETTING:key\n` | Read one setting | `SETTING:key:value` / `STATUS:ERR:KEY` |
| `SET_SETTING:key:value\n` | Write one setting. **RAM only — not persisted until `SAVE`.** | `STATUS:OK:SET_SETTING:key:value` / `STATUS:ERR:*` |

#### Settings keys

| Key | Internal range | Meaning |
|---|---|---|
| `overheat` | 0–100 | Overheat stop temperature (°C) |
| `limit_volt` | 30–90 | Max voltage limit. Actual V = value × 0.1 (3.0–9.0V) |
| `limit_current` | 5–45 | Over-current stop threshold. Actual A = value × 0.1 (0.5–4.5A) |
| `brightness` | 0–16 | Display brightness |
| `measure_step` | 0–2 | RPM measurement step. 0=final, 1=first, 2=all steps |
| `cheer_up` | 0–30 | Low-voltage assist threshold. 0=none. Actual V = value × 0.1 |
| `pulse_v` | 0–limit_volt | Pulse break-in voltage. Actual V = value × 0.1 |
| `pulse_sec` | 1–9 | Pulse break-in cycle period (seconds) |
| `pulse_pattern` | 0–1 | Pulse pattern. 0=ON/OFF, 1=Linear |
| `buzzer_volume` | 0–5 | Buzzer volume. 0=OFF |

### 3-5. Summary log retrieval

| Command | Response |
|---|---|
| `GET_LOG\n` | `LOG:HEAD` / `LOG:STEP` × (cycles × steps) / `LOG:CYC` × cycles / `LOG:END` |

#### LOG response format

```
LOG:HEAD,progno,lastcycle,rotate_total
LOG:STEP,cycle,step,lastrpm,maxrpm,kv,voltage,current_ma,direction,runtime_sec,cooltime_sec,temp,overheat
LOG:CYC,cycle,rotate_sum
LOG:END
```

| Field | Unit / Notes |
|---|---|
| `lastrpm` / `maxrpm` | Internal value. Actual RPM = value × 10 |
| `voltage` | Internal value × 0.1V. **Different unit to CSV stream col10 (mV).** e.g. 30 = 3.0V |
| `current_ma` | mA |
| `direction` | 0–4 (direction encoding table) |
| `overheat` | 0 = normal, 1 = overheat occurred |
| `rotate_sum` / `rotate_total` | Internal pulse count values |

### 3-6. EEPROM save

| Command | Action | Response |
|---|---|---|
| `SAVE\n` | Write all programs and settings from RAM to EEPROM. Persists across power-off. | `STATUS:OK:SAVE` |

> ⚠️ **EEPROM has finite write cycle life.** Never send `SAVE` automatically or on a timer. It must be an explicit deliberate user action. Batch all changes then save once.

---

## MBC2→PC: STATUS messages

### Async notifications (device-initiated, no command needed)

| Message | Trigger |
|---|---|
| `STATUS:COOLING` | Device transitions to cooling state (`run_state=2`) |
| `STATUS:LOW_AMP_LIMIT` | CC control detects instability (oscillation at low current setting) |

### Error responses

| Message | Condition |
|---|---|
| `STATUS:ERR` | Unknown command |
| `STATUS:ERR:FORMAT` | Malformed command (missing delimiter etc.) |
| `STATUS:ERR:PROG_NO` | Program number out of range (not 1–50), or No.0 |
| `STATUS:ERR:COUNT` | `SET_PROG` did not have exactly 27 values |
| `STATUS:ERR:RANGE` | Value out of allowed range |
| `STATUS:ERR:KEY` | Setting key does not exist |
| `STATUS:ERR:NOT_RUNNING` | `PAUSE` or `NEXT_STEP` sent when not running |
| `STATUS:ERR:ALREADY_PAUSED` | `PAUSE` sent when already paused |
| `STATUS:ERR:NOT_PAUSED` | `RESUME` sent when not paused |

---

## Encodings

### Character table (program name, name0–3)

4-character fixed-length name. Each character is an integer 0–36.

```
Index: 0  → ' ' (space)
Index: 1–10 → '0'–'9'
Index: 11–36 → 'A'–'Z'
```

Full table string: `" 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"`

Example: `[30, 31, 24, 15]` → `"TUNE"`

### Time index (runtime / cooltime, 0–77)

Non-linear encoding. GET_PROG/SET_PROG uses the index value, not seconds.

| Index range | Formula (→ seconds) | Real time range | Step |
|---|---|---|---|
| 0–17 | seconds = index × 10 | 0–170s | 10s |
| 18–44 | seconds = (index − 15) × 60 | 3–29 min | 1 min |
| 45–66 | seconds = (index − 42) × 600 | 30–240 min | 10 min |
| 67–77 | seconds = (index − 62) × 3600 | 5–15 hours | 1 hour |

### Direction encoding

| Value | Meaning |
|---|---|
| 0 | OFF / not set |
| 1 | Normal (forward) |
| 2 | Reverse |
| 3 | Normal Pulse (pulse break-in, forward) |
| 4 | Reverse Pulse (pulse break-in, reverse) |

> **For Mini 4WD break-in, always use direction 2 (Reverse).** This applies to all chassis types (FM-A, Super-FM, MA, MS, etc.).

### Voltage contexts (different units in different contexts)

| Context | Unit | Example |
|---|---|---|
| CSV stream col10 (`voltage_mv`) | mV | 2891 = 2.891V |
| CSV stream col11 (`set_voltage_mv`) | mV (run_setvolt × 100) | 3000 = 3.0V |
| `SET_VOLTAGE` command argument | V (float) | `2.5` |
| GET/SET_PROG `volt` field | Internal (× 0.1V) | 25 = 2.5V |
| GET/SET_SETTING `limit_volt` | Internal (× 0.1V) | 30 = 3.0V |
| GET_LOG `voltage` field | Internal (× 0.1V) | 30 = 3.0V |

### Parsing rules

- Lines starting with `Debug:` → **ignore entirely**
- Lines starting with `STATUS:` → status/ACK/error message
- Lines starting with `PROG:` → program data response
- Lines starting with `SETTING:` → settings data response
- Lines starting with `LOG:` → summary log data
- All other non-empty lines during a run → CSV telemetry data

---

## Appendix — v0.200(Beta) additions (unofficial)

**Not from mic-LABO.** Observed on hardware 2026-08-08. The v0.200 user guide
states AccelTest has no USB export; it emits the following anyway. Treat as
provisional.

### New commands (verified working)

| Command | Response |
|---|---|
| `GET_CALIB` | `CALIB:norm_volt:n` `CALIB:rev_volt:n` `CALIB:current:n` `CALIB:temp:n` |
| `SET_CALIB:…` | `STATUS:OK:SET_CALIB:…` — **arguments and units unknown; do not send** |
| `GET_WIFI` | `WIFI:STATUS:…` (e.g. `DISCONNECTED`), and `WIFI:IP:` / `WIFI:RSSI:` when connected |
| `SET_WIFI:…` | `STATUS:OK:WIFI_CONNECTING` — argument format unknown |

Calibration read from one device: `norm_volt:10000`, `rev_volt:10000`,
`current:9300`, `temp:0`. Apparently ×10000 scale factors (1.0000, 1.0000,
0.9300) with a temperature offset, but that reading is inferred.

### AccelTest output

AccelTest measures load characteristics — predicted RPM at no-load, low-load and
high-load — by varying voltage automatically. One pass per direction; a two-pass
run took 173 s. Emitted during a run:

```
ACCEL_CK,<pass>,…                     once per pass, before the stall sweep
ACCEL_STALL,<pass>,<n>,…              five per pass, n = 0..4, ~14 s apart
ACCEL_LOAD,<pass>,<No>,…,<Lo>,…,<Hi>,…   once per pass
ACCEL_DONE,…                          once, at the end
```

**`ACCEL_DONE` is confirmed** against the device's own results screen:

```
ACCEL_DONE,1,19080,15713,8970,1,18980,15634,8918
             └ normal: No,Lo,Hi ┘   └ reverse: No,Lo,Hi ┘
```

Both groups are preceded by `1` — a flag of some kind, not the direction;
direction is positional (normal first, then reverse), and is corroborated by
CSV `col12` reading 1 during pass 1 and 2 during pass 2.

**`ACCEL_LOAD`**, mostly decoded by running the same test at two voltages:

```
ACCEL_LOAD,<pass>,<No_rpm>,<No_mA>,<R_mohm?>,<?>,<Lo_rpm>,<Lo_mA>,<Hi_rpm>,<Hi_mA>

3.0V  ACCEL_LOAD,1,19080,749,1441,5660,15713,831,8970,2190
4.0V  ACCEL_LOAD,1,24060,743,1527,8071,21090,829,15125,2114
```

| Field | 3.0V (p1/p2) | 4.0V (p1/p2) | Reading |
|---|---|---|---|
| No RPM | 19080 / 18980 | 24060 / 24540 | rises with voltage ✓ |
| No mA | 749 / 754 | 743 / 788 | **constant** |
| f5 | 1441 / 1451 | 1527 / 1496 | near-constant — resistance in mΩ, probable |
| f6 | 5660 / 5656 | 8071 / 7436 | **unexplained** |
| Lo RPM | 15713 / 15634 | 21090 / 21247 | rises ✓ |
| Lo mA | 831 / 820 | 829 / 837 | **constant** |
| Hi RPM | 8970 / 8918 | 15125 / 14645 | rises ✓ |
| Hi mA | 2190 / 2174 | 2114 / 2150 | **constant** |

**The load levels are defined by current, not voltage.** Raising the test
voltage by a third left all three current figures unchanged while every RPM
rose. Currents do not stay fixed under a voltage increase unless they are the
quantity being held fixed — so AccelTest reports **the RPM the motor achieves at
three fixed current draws**. Confirmed on two motors at two voltages each.

**The current targets are per motor, not device constants.** A second box-stock
motor gave ~700 / ~790 / ~1900 mA against the first motor's ~750 / ~830 /
~2150 mA — steady across voltage within each motor, but 5–12% lower throughout.
The device evidently derives them during the `ACCEL_CK` / `ACCEL_STALL` phase.
**Anything storing these results must record the actual currents**; two motors'
RPMs are measured at similar, not identical, loads.

**f5 is probably winding resistance in mΩ.** Steady within a motor (1441/1451),
clearly different between motors (1653/1651 for the second), and it rises a few
percent as the motor warms — 1441 → 1527 and 1653 → 1791 between the 3.0V and
4.0V runs. The physics is self-consistent: the higher-resistance motor drew less
current *and* ran slower off-load. Three independent observations agreeing, but
still not confirmed by mic-LABO.

**f6 was wrongly guessed as kV in an earlier revision of this file.** It is not:
kV is a motor constant and would not move, but f6 went 5660 → 8071, and the two
passes at 4.0V disagree by 8% where every other field agrees within 2%. Across
four runs it scales roughly with voltage (×1.3–1.5 for a ×1.33 change) but too
noisily to pin down. Left undocumented rather than assigned a plausible-sounding
meaning.

`ACCEL_STALL` fields beyond `<pass>,<n>` are undecoded. Firmware also contains a
`STALL_HEAD,duty,volt_mv,current_ma,pulses,i_early,i_late` header that neither
run emitted — presumably a separate test we have not triggered.

### No way to start these tests over serial

The firmware contains no command to begin an AccelTest — the strings include
`ACCEL_ABORT` but nothing resembling `START_ACCEL`. The test is started from the
device's own menus, and the app can only listen. Anything built on this data has
to be **passive capture**: the user runs the test on the device, the app notices
the `ACCEL_*` lines and records them.
