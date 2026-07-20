@echo off
title MBC2 Dashboard - Build EXE
REM ================================================================
REM  Builds dist\MBC2Dashboard.exe — single-file server app
REM  (no native window; opens Chrome/Edge after binding port 8766)
REM  bundles: server.py, mbc2-dashboard.html, schema.sql,
REM           default_programs.json, VERSION, icon.ico
REM
REM  IMPORTANT: run this script with an x64 Python on PATH.
REM  This machine is ARM64; an ARM64 build won't run on x64 PCs.
REM  See BUILD.md for the recommended interpreter path.
REM
REM  One-time setup:
REM    python -m pip install pyinstaller
REM ================================================================
setlocal
cd /d "%~dp0.."
set /p APPVERSION=<VERSION
echo.
echo  Building MBC2 Dashboard v%APPVERSION% ...
echo.

python -m PyInstaller --noconfirm --clean MBC2Dashboard.spec

if not exist "dist\MBC2Dashboard.exe" (
    echo.
    echo  BUILD FAILED - see errors above.
    pause
    exit /b 1
)

echo.
echo  ==========================================
echo   Build complete: dist\MBC2Dashboard.exe  ^(v%APPVERSION%^)
echo  ==========================================
echo.
pause
