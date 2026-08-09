# MBC2 Dashboard — Build Guide

## x64 Python — CRITICAL

This dev machine is ARM64 (Microsoft Surface X). **Always build with an x64 Python.**
An ARM64 build produces an exe that x64 machines cannot run.

Install a dedicated x64 CPython 3.11 or 3.12 from python.org
(use the *Windows installer (64-bit)* download, not the ARM64 one).

Confirm the active interpreter before building:

    python -c "import platform; print(platform.machine())"
    # must print: AMD64

Install the build dependencies into that interpreter:

    python -m pip install pyinstaller pyserial pywebview

---

## Building from a clean checkout

**Important:** always build from a clean git checkout — never from a working
folder that has a live `mbc2.db`. The published packages must not contain any
motor session data or club programs.

```bat
git clone <repo-url> mbc2-build
cd mbc2-build
git checkout v4.0      REM or the tag you are releasing
```

---

## Run the tests first

    node tests/test_program_timing.js

Exit 0 is a pass. These cover the break-in program runner's step timing, which
is the part of the app that can silently run a motor for the wrong length of
time. See [`tests/README.md`](tests/README.md).

Node is a **developer tool only** — nothing in the build or the shipped package
depends on it. If Node is not installed, skip this step.

---

## Build the Windows exe

    windows\BUILD EXE (developer use only).bat

Reads version from `app\VERSION`. Output: `dist\MBC2Dashboard.exe`

## Build the Windows installer + USB zip (one step)

    windows\BUILD INSTALLER (developer use only).bat

Requires Inno Setup 6:

    winget install JRSoftware.InnoSetup

Output:
- `dist\installer\MBC2Dashboard-Setup-<ver>.exe`
- `dist\MBC2Dashboard-WindowsPortable-<ver>.zip`

## Build the Mac package

    mac\BUILD MAC PACKAGE (developer use only).bat

Runs on Windows. Output: `dist\MBC2Dashboard-Mac-<ver>.zip`

### Do not change how that zip is written

The zip is built by `mac\make-mac-zip.ps1`, which writes entries directly via
`System.IO.Compression`. Both obvious alternatives are broken, and both fail
only once the package reaches a Mac:

- **`Compress-Archive`** (PowerShell 5.1) writes **backslash** path separators.
  The zip spec requires forward slashes, and macOS may extract the tree as flat
  files literally named `MBC2Dashboard\app\server.py`, leaving the launcher
  unable to find `app/server.py`. **The shipped v4.0.1 Mac zip had this.**
- **`tar.exe`** (bsdtar) writes forward slashes correctly but **pads the archive
  to a 10240-byte block**, leaving trailing zeros after the end-of-central-
  directory record. Strict readers reject the file outright — Python's
  `zipfile` and .NET both refuse to open it.

The script also sets the Unix execute bit (`ExternalAttributes`) on the
`.command`, which neither alternative can do, and verifies its own output: it
fails the build on backslashes, an empty archive, or a launcher that is not
marked executable.

Note the Mac package is **source + browser**, not a PyInstaller `.app`. There is
no pywebview, no `.icns`, no App Transport Security plist and no Gatekeeper
notarization involved. If that ever changes, most of the macOS packaging
literature that does not currently apply suddenly will.

---

## Bat file encoding note (ASCII-bat gotcha)

Windows batch files **must be saved as ASCII** (or Windows-1252 without BOM).
If a `.bat` is saved as UTF-8 with BOM, `cmd.exe` may misread the first line
and produce `'@echo' is not recognized` or silent failures. The build bats in
this repo contain only ASCII characters for this reason.

---

## Verify the dist/ output before releasing

```
dist\installer\MBC2Dashboard-Setup-<ver>.exe   should exist
dist\MBC2Dashboard-WindowsPortable-<ver>.zip   should contain:
    MBC2Dashboard\MBC2Dashboard.exe
    MBC2Dashboard\Start MBC2 (USB).bat
    MBC2Dashboard\Start MBC2 (this PC).bat
    MBC2Dashboard\README.txt
dist\MBC2Dashboard-Mac-<ver>.zip               should contain:
    MBC2Dashboard/Start MBC2 Dashboard.command   (note: forward slashes,
    MBC2Dashboard/README.txt                      and -rwxr-xr-x on the
    MBC2Dashboard/app/server.py                   .command)
```

The build fails itself on the zip checks, but to inspect a zip by hand:

```
python -c "import zipfile,stat; z=zipfile.ZipFile(r'dist\MBC2Dashboard-Mac-4.0.1.zip'); [print(stat.filemode(i.external_attr>>16), i.filename) for i in z.infolist()]"
```

Opening without error proves the central directory is intact; the mode column
must show `-rwxr-xr-x` on the `.command`, and no filename may contain a
backslash.

**Verify no `.db` files are in the dist output** before publishing.

---

## Release build record

Record interpreter and PyInstaller version each time a release build is cut.

| Version | Date | Python x64 path | PyInstaller |
|---|---|---|---|
| 4.0 | 2026-07-20 | `C:\Users\Kris.Pawson\AppData\Local\Python\pythoncore-3.14-64\python.exe` (3.14.4 AMD64) | 6.21.0 |
| 4.0 (pywebview) | 2026-07-20 | same as above | 6.21.0 (+ pywebview 6.2.1, pyserial 3.5) |
| 4.0 (rebuild, commit `0935ce1`) | 2026-08-06 | same as above | 6.21.0 (+ pywebview 6.2.1, pyserial 3.5) |
| 4.0 (DPI fix, commit `22a05c3`) | 2026-08-06 | same as above | 6.21.0 (+ pywebview 6.2.1, pyserial 3.5) |
| 4.0 (test-matrix fixes, commit `cb3fe64`) | 2026-08-07 | same as above | 6.21.0 (+ pywebview 6.2.1, pyserial 3.5) |
| **4.0 RELEASE, commit `c335703`** | 2026-08-07 | same as above | 6.21.0 (+ pywebview 6.2.1, pyserial 3.5) |
| **4.0.1, commit `06c0897`** | 2026-08-07 | same as above | 6.21.0 (+ pywebview 6.2.1, pyserial 3.5) |
| **4.0.1, commit `194b0b3`** | 2026-08-09 | same as above | 6.21.0 (+ pywebview 6.2.1, pyserial 3.5) |

The 2026-08-06 rebuild replaced artefacts that had been built *before* the
pywebview commit and therefore still shipped the browser-based app. If the
installer is ~12 MB rather than ~24 MB, it is a pre-4.5 build — discard it.

**4.0.1 build, 2026-08-07, commit `06c0897`.** Clean clone; all four artefacts
pick the version up from `app/VERSION`, so they are named `-4.0.1`. Verified:
PE machine `0x8664`, no `.db` anywhere, Mac `.command` LF-only, no club
programs, `VERSION` inside the Mac zip reads `4.0.1`. Smoke test: window titled
`MBC2 Dashboard v4.0.1`, `/api/info` → `{"version": "4.0.1"}`, clean shutdown.
Launch to serving: **5.9 s cold, 1.9 s warm** — the cold figure is a
first-run cost (PyInstaller unpacking ~21 MB, Defender scanning a new binary)
and is not representative; always measure warm.

⚠ `dist/` now holds **4.0.1** artefacts. The `v4.0` tag's artefacts are *not*
here any more — rebuild them from the tag if a v4.0 GitHub release is ever cut.

**4.0.1 rebuild, 2026-08-09, commit `194b0b3`.** Clean clone of `main`, covering
the AccelTest results panel, the Mac zip fix, the program step-timing fix and
window centring. `node tests/test_program_timing.js` passed in the clone before
building. Sizes: exe 21.28 MB, installer 23.04 MB, portable zip 21.08 MB, Mac
zip 0.10 MB. Verified: PE machine `0x8664`; no `.db` anywhere in `dist/`; no
PMPE/SPRF in the bundled `default_programs.json`; Mac zip opens with a valid
central directory, forward slashes throughout, `.command` at `-rwxr-xr-x` with
LF endings. Smoke test: `/api/info` → `{"version": "4.0.1"}`, `/api/accel`
returned the stored test, the served page carried the new AccelTest panel and
`appRunCheckDeadline`, `/api/shutdown` released the port cleanly. Window
measured on screen at 1400x852 in a 1536x912 work area — 68 px clear each side,
30 px top and bottom. Launch to serving **2.36 s warm**.

⚠ Not verified in this build: the AccelTest panel has not been looked at on
screen, and nothing here has been run on a Mac.

**Release build, 2026-08-07, commit `c335703`.** Cut from a clean clone of
`main` after the app-driven runner, ACK checking and connection-close work.
Sizes: exe 21.28 MB, installer 23.04 MB, portable zip 21.07 MB, Mac zip
0.09 MB. Verified: PE machine `0x8664`; both zips match the checklist above; no
`.db` in `dist/` or inside either zip; no PMPE/SPRF in the bundled
`default_programs.json`; Mac `.command` LF-only (0 CRLF). Smoke test against a
scratch data dir: fresh DB seeded, daily backup written, `/api/info` → 4.0,
native window titled `MBC2 Dashboard v4.0`, `/api/ports` enumerated
`COM8 — USB-SERIAL CH340`, and the served page confirmed to carry the relative
`API`, the app-driven runner and the ACK checking. `/api/shutdown` returned 200
with no orphaned process and the port released.

The earlier 2026-08-07 rebuild was the first to be cut from a clean clone of `main`
(commit `cb3fe64`) rather than the `v4-packaging` branch, and the first to
carry the installer shutdown-wait and splash-dismissal fixes. Sizes: exe
21.3 MB, installer 23.0 MB, portable zip 21.1 MB, Mac zip 0.08 MB. Verified:
PE machine `0x8664` (x64); zip contents match the checklist above; no `.db`
anywhere in `dist/` or inside either zip; no PMPE/SPRF in the bundled
`default_programs.json`; the Mac `.command` still has LF-only endings.
Smoke-tested from a scratch data dir — fresh DB seeded, daily backup written,
`/api/info` → `{"version":"4.0"}`, native window titled `MBC2 Dashboard v4.0`,
and `/api/ports` enumerated the attached device as
`COM8 — USB-SERIAL CH340`. Installing over a running instance returned exit 0
in 11 s with no orphaned process.
