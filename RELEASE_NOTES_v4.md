# MBC2 Dashboard v4.0 — Release Notes

*DRAFT — complete after hardware test matrix passes*

---

## What's new in v4

### It's a real app now — no browser required

v3.x ran in a Chrome tab because the browser owned the USB connection. In v4
the connection moved into the app's own Python backend, which freed the
dashboard from the browser entirely. The Windows version now opens in its own
window with its own icon in the taskbar.

Two things follow from this:

- **Chrome is no longer required on Windows.** Firefox-only and Safari-only
  machines can run the installer and portable builds.
- **Pick your COM port from a dropdown.** Instead of Chrome's port-permission
  prompt, the app lists the ports it can see, with a refresh button for when
  you plug the MBC2 in after starting.

Running from source (and the Mac package) still opens in a browser — but any
modern browser now works, not just Chrome.

### Run your own programs on the device

Programs you build in the app used to be for reference only — the MBC2 can
only run what is in one of its own 50 slots, so selecting one of your programs
and pressing start just ran the motor manually.

**Push & Run** fixes that: pick one of your programs, pick a slot, and the app
writes it to the device and starts it. The write goes to the device's **memory
only — SAVE is never sent** — so whatever was stored in that slot comes back
after a power cycle, and no EEPROM write cycles are used.

The two program lists now sit together under **Break-in Program**, labelled
"In this app" and "On the device", so it is obvious which is which.

### Manual runs are recorded

Starting the motor manually auto-starts a session, but those sessions used to
save with no data in them — the recorder was waiting for a named program to
begin. Manual runs are now recorded properly.

### One-click Windows installer

Download `MBC2Dashboard-Setup-4.0.exe`, run it, and a desktop icon appears.
No Python, no bat files, no zip juggling.

### Your motor data is permanently safe

In v3.x the database lived beside the app, which meant a bad update or
reinstall could theoretically reach it. In v4 the database **permanently**
moves to a separate folder the installer never touches:

    %LOCALAPPDATA%\MBC2Dashboard\mbc2.db

This separation is by construction — the Inno Setup script does not include
`mbc2.db` in the `[Files]` section and cannot reach the data folder.

### Automatic daily backups

Every time the app starts it checks whether today's backup exists. If not,
it writes `%LOCALAPPDATA%\MBC2Dashboard\backups\mbc2-YYYY-MM-DD.db` using
SQLite's own backup API (which correctly checkpoints any WAL file). The last
14 daily backups are kept automatically.

### USB / portable mode

Unzip `MBC2Dashboard-WindowsPortable-4.0.zip` to a USB stick and double-click
`Start MBC2 (USB).bat`. Sessions are saved to a `data\` folder on the stick
and travel with it between machines. The host PC needs the CH340 driver — no
browser and no Python, as stated in the README.

---

## Upgrading from v3.x

### Installed exe over an old zip

On the first launch of v4, if a `mbc2.db` is found **beside the exe** and no
database exists in the new home yet, it is **copied** (never moved) to
`%LOCALAPPDATA%\MBC2Dashboard\mbc2.db`. The original is left in place as a
fossil backup. The app shows a one-time notice with the new location.

The source path is wherever the exe lives — so if you run the new
`MBC2Dashboard.exe` from inside your old v3.x folder, the migration will find
the v3.x database automatically.

### Installer over a zip (data appears to be missing)

If you ran the installer without first running the exe from the old folder,
the installer puts the app in `%LOCALAPPDATA%\Programs\MBC2Dashboard\` and
the auto-migration won't find the old `mbc2.db` (which is in a different
folder). Your data is **not lost** — copy your old `mbc2.db` into
`%LOCALAPPDATA%\MBC2Dashboard\` manually, then launch the app.

---

## Known issues / SmartScreen

The exe is not code-signed (cost deferred). Windows will show:

> Windows protected your PC

Click **More info** → **Run anyway**.

*TODO: add SmartScreen screenshot here before publishing.*

---

## CH340 driver — ARM64 machines

Surface Pro X, Copilot+ PCs, and other ARM64 Windows machines need the CH340
driver pinned at **v3.9.2024.9**. Newer releases dropped ARM64 support.

The ARM64 driver can be obtained from Kris or from the mic-LABO community.
The standard CH340 download page: https://www.wch-ic.com/downloads/CH341SER_EXE.html

---

## Compatibility

- Old databases into v4: always works. Schema auto-migrates on launch.
- New v4 databases into v3.x: unsupported. The startup backup is the recovery path.
- CSV export remains the universal per-session format. Copy `mbc2.db` into the
  data home of any equal-or-newer version for whole-history transfer.

---

## Mac package

The Mac package (`MBC2Dashboard-Mac-4.0.zip`) is provided as a convenience but
is **UNTESTED** — the developers run Windows. It contains Python source files
and a launcher `.command` script, and it opens in a browser rather than a
native window.

Requirements: Python 3, the `pyserial` package
(`python3 -m pip install --user pyserial` — the launcher warns if it's
missing), a browser, and the Mac CH340 driver. Please report issues via
GitHub.
