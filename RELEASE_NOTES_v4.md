# MBC2 Dashboard v4 — Release Notes

*v4.0 tagged 2026-08-07. Still a draft: USB mode has not been tried on a second
machine, the Mac package is untested on a real Mac, and no full 3-minute
baseline benchmark has been recorded. The AccelTest features in 4.0.1 need
firmware v0.200+ on the device.*

---

## 4.0.1

### AccelTest results are recorded and shown

If your MBC2 is on firmware **v0.200 or newer** it has an **AccelTest** in its
own menu. It spins the motor up and then loads it, reporting the speed the motor
still holds at three levels of load.

Run it from the device as usual — there is no way to start it from the app — and
the app now records the result automatically. Results appear under
**Motors → AccelTest**, and on each motor's own record.

Each result shows, per direction:

- **No load / Low load / High load** — the RPM the motor held, with the current
  it drew to get there
- **Load retention** — the high-load RPM as a percentage of the no-load RPM

Load retention is the number worth caring about. It is how well a motor holds
its speed when it is actually working, and peak RPM cannot tell you: a
Torque-Tuned 2 and a box-stock motor measured within 2% of each other spinning
free, and 63% apart under load.

Two things to know:

- **Select the motor before you start the test.** If you forget, the result is
  still saved — it just arrives unattributed, and you can attach it to a motor
  afterwards from the AccelTest tab.
- **Only compare results taken at the same voltage**, which is shown at the top
  of every result.

### Break-in programs keep proper time in the background

If you minimised the app during a program run, a step could carry on past the
time it was meant to stop — Windows and browsers deliberately slow down timers
in windows you are not looking at, and the app was relying on one of those
timers to end each step. The motor ran longer than the program asked for and
nothing said so.

Step timing no longer depends on that. If a step does somehow end late, the app
now tells you during the run and again at the end, so you know that session did
not follow the program it says it did.

### It starts faster, and opens in the middle of the screen

The app used to spend about three seconds on every launch checking whether a
copy was already running — time spent waiting on a check that could never answer
any quicker. It now opens in about two seconds.

The window also opens centred, instead of low and to the right.

### Mac package fixed

The Mac zip was built incorrectly and would probably not have worked. It is
rebuilt properly, and the launcher no longer needs the manual `chmod` step. The
Mac package is **still untested on a real Mac** — this fixes a fault found by
inspection.

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

### Run your own programs

Programs you build in the app used to be for reference only — selecting one
and pressing start just ran the motor manually.

Now the app runs them. Pick a program under **In this app**, press **START
PROG**, and the app takes the MBC2 through each step for you: direction,
voltage, how long to run, how long to cool, repeated for the number of cycles
you set. **STOP**, **PAUSE** and **NEXT** control the run, and the panel shows
which cycle and step you are on with the time remaining.

Nothing is written to the device to make this work. The device's own 50 slots
are still there for when you want to run the MBC2 on the bench **without the
laptop** — Settings → Program Sync will read all 50 slots at once, save one
into your library (handy if you copy someone's program at a race meet), or
write one of yours into a slot. Writing a slot changes the device's **memory
only — SAVE is never sent** — so whatever was stored there comes back after a
power cycle, and no EEPROM write cycles are used.

### It tells you when the device disagrees

The app used to send a command and assume it worked. Now it reads the device's
reply. If your voltage limit holds a step below what the program asked for,
you get a warning saying what was asked for and what was actually applied,
instead of a break-in quietly running at the wrong voltage.

Closing the window while recording now asks first — but only if there is
something to lose.

### Manual runs are recorded

Starting the motor manually auto-starts a session, but those sessions used to
save with no data in them — the recorder was waiting for a named program to
begin. Manual runs are now recorded properly.

### One-click Windows installer

Download `MBC2Dashboard-Setup-<version>.exe`, run it, and a desktop icon appears.
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

Unzip `MBC2Dashboard-WindowsPortable-<version>.zip` to a USB stick and double-click
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

The exe is not code-signed (cost deferred), so Windows may show:

> Windows protected your PC

Click **More info** → **Run anyway**.

Whether it appears depends on how the installer reached the machine, not on
the machine itself. Browsers and email clients tag downloaded files with a
"mark of the web", and that tag is what SmartScreen reacts to. So a download
from the GitHub release page will usually trigger it, while the same installer
copied from a USB stick or a network share typically will not — confirmed on
2026-08-07, when a USB-copied install produced no warning at all.

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

The Mac package (`MBC2Dashboard-Mac-<version>.zip`) is provided as a convenience
but is **UNTESTED** — the developers run Windows. It contains Python source
files and a launcher `.command` script, and it opens in a browser rather than a
native window.

Requirements: Python 3, the `pyserial` package
(`python3 -m pip install --user pyserial` — the launcher warns if it's
missing), a browser, and the Mac CH340 driver. Please report issues via
GitHub.

On first launch macOS will refuse to open it, because the package is not signed
by a registered Apple developer. Depending on your macOS version the message is
either "cannot be verified" or the more alarming **"is damaged and can't be
opened"** — the second one is false, and it is not a sign the download went
wrong. Either way: **right-click the `.command` → Open → Open**, once, and it
will run normally from then on.
