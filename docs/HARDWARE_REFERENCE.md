# MBC2 Dashboard — Hardware Reference

## MBC2 Device

| Item | Detail |
|---|---|
| Manufacturer | mic-LABO (Michihiro Nakagawa) |
| MCU | ESP32-WROOM-32 |
| USB bridge | CH340 |
| Baud rate | 115200 |
| Firmware target | v0.110+ (bidirectional serial support) |
| OTA firmware server | esp32.miclabo.xyz |

**Known hardware issue:** The MBC2 crashes reproducibly at Round 2, Step 5 (~63 minutes into a session) with an audible crackle/pop. Root cause: motor-generated electrical noise causing GND fluctuation and ESP32 brownout. Documented across 12+ PCB revisions by Michihiro on note.com. Observed specifically with Power Dash motor.

**Hardware mitigations in progress:**
- ATX PSU breakout board (AliExpress) — cleaner power supply, eliminate noise from cheap PSU
- 100nF 50V ceramic capacitors (Jaycar RC5360) soldered across motor output pads — noise snubber. Ceramic caps are non-polarised (orientation irrelevant).

---

## Host machine

| Item | Detail |
|---|---|
| Device | Microsoft Surface X |
| Architecture | ARM64 |
| OS | Windows |
| Required CH340 driver | v3.9.2024.9 specifically |

> **Driver note:** Newer CH340 driver versions dropped ARM64 support. Do not suggest updating the driver. The version above is the correct one for this hardware.

---

## Mini 4WD context

The app is used for competitive Tamiya Mini 4WD motor break-in. Key domain facts:

- **Break-in direction:** Always `R` (Reverse) for all chassis types — FM-A, Super-FM, MA, MS, ME
- **Single-shaft motors** suit front/rear mount chassis (FM-A, Super-FM, Type 3, etc.)
- **Dual-shaft PRO motors** suit midship chassis (MA, MS, ME)
- **Motor identifier format:** `MODEL-DIRECTION-NUMBER` e.g. `SD-R-01` (Sprint Dash, Reverse, unit 1). Sequential numbering resets per model code.
- **Label format:** 5mm cut label tape

### Break-in process (confirmed sequence)

1. Contact cleaner flush
2. 1 minute dry
3. Light oil on bushings only
4. Run break-in program (no oil between programs)
5. Contact cleaner flush
6. Light oil
7. Baseline test

### Community RPM benchmarks

- Sprint Dash at 3V: 38–40K+ RPM is the Southeast Asian Mini 4WD community benchmark

### Motor efficiency scoring (implemented)

- 40% weighted vs Tamiya published RPM spec
- 40% weighted vs best same-model peer in motor registry
- 20% thermal
