# MBC2 Dashboard — Build Guide

## x64 Python — CRITICAL

This dev machine is ARM64 (Microsoft Surface X). **Always build with an x64 Python.**
An ARM64 build produces an exe that x64 machines cannot run.

Install a dedicated x64 CPython 3.11 or 3.12 from python.org
(use the *Windows installer (64-bit)* download, not the ARM64 one).

Confirm the active interpreter before building:

    python -c "import platform; print(platform.machine())"
    # must print: AMD64

Install the build dependency into that interpreter:

    python -m pip install pyinstaller

## Building the exe

Run `windows\BUILD EXE (developer use only).bat` — it reads `VERSION`,
calls `pyinstaller --clean MBC2Dashboard.spec`, and prints the output path.

Output: `dist\MBC2Dashboard.exe`

## Release build record

Record interpreter and PyInstaller version each time a release build is cut.

| Version | Date | Python x64 path | PyInstaller |
|---|---|---|---|
| *(none yet)* | | | |

---

*This file will be expanded in Phase 4 with the full clean-checkout guide,
USB zip procedure, installer build steps, and Mac package steps.*
