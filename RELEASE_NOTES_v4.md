# MBC2 Dashboard v4.0 — Release Notes

*DRAFT — complete after hardware test matrix passes*

---

## What's new in v4

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
and travel with it between machines. The stick needs Chrome and the CH340
driver on the host PC — stated in the README.

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
and a launcher `.command` script. Requirements: Python 3 + Chrome/Edge + CH340
driver for Mac. Please report issues via GitHub.
