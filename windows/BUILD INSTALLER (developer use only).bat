@echo off
title MBC2 Dashboard - Build Windows Packages
REM ================================================================
REM  Builds BOTH Windows packages into dist\:
REM    1. dist\installer\MBC2Dashboard-Setup-<ver>.exe  (installer)
REM    2. dist\MBC2Dashboard-WindowsPortable-<ver>.zip  (USB/portable)
REM
REM  IMPORTANT: run this script with an x64 Python on PATH.
REM  See BUILD.md for the recommended interpreter path.
REM
REM  Requires:
REM    python -m pip install pyinstaller
REM    Inno Setup 6  (winget install JRSoftware.InnoSetup)
REM ================================================================
setlocal
cd /d "%~dp0.."
set /p APPVERSION=<app\VERSION
echo.
echo  [1/3] Building MBC2Dashboard.exe v%APPVERSION% ...
echo.

python -m PyInstaller --noconfirm --clean MBC2Dashboard.spec

if not exist "dist\MBC2Dashboard.exe" (
    echo.
    echo  EXE BUILD FAILED - see errors above.
    pause
    exit /b 1
)

echo.
echo  [2/3] Building installer ...
echo.

set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    echo  ERROR: Inno Setup 6 not found.
    echo  Install with:  winget install JRSoftware.InnoSetup
    pause
    exit /b 1
)

%ISCC% /Q "windows\MBC2Dashboard.iss"
if errorlevel 1 (
    echo.
    echo  INSTALLER BUILD FAILED - see errors above.
    pause
    exit /b 1
)

echo.
echo  [3/3] Building portable/USB zip ...
echo.

set STAGE=dist\usb-stage\MBC2Dashboard
if exist "dist\usb-stage" rmdir /s /q "dist\usb-stage"
mkdir "%STAGE%"

copy /y "dist\MBC2Dashboard.exe"            "%STAGE%\" >nul
copy /y "windows\Start MBC2 (USB).bat"      "%STAGE%\" >nul
copy /y "windows\Start MBC2 (this PC).bat"  "%STAGE%\" >nul
copy /y "windows\README.txt"                "%STAGE%\" >nul

powershell -Command "Compress-Archive -Force -Path 'dist\usb-stage\MBC2Dashboard' -DestinationPath 'dist\MBC2Dashboard-WindowsPortable-%APPVERSION%.zip'"
rmdir /s /q "dist\usb-stage"

if not exist "dist\MBC2Dashboard-WindowsPortable-%APPVERSION%.zip" (
    echo.
    echo  ZIP BUILD FAILED.
    pause
    exit /b 1
)

echo.
echo  ==========================================
echo   Done:
echo    dist\installer\MBC2Dashboard-Setup-%APPVERSION%.exe
echo    dist\MBC2Dashboard-WindowsPortable-%APPVERSION%.zip
echo  ==========================================
echo.
pause
