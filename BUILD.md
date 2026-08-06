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
    MBC2Dashboard\Start MBC2 Dashboard.command
    MBC2Dashboard\README.txt
    MBC2Dashboard\app\server.py  (and other app files)
```

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

The 2026-08-06 rebuild replaced artefacts that had been built *before* the
pywebview commit and therefore still shipped the browser-based app. If the
installer is ~12 MB rather than ~24 MB, it is a pre-4.5 build — discard it.
