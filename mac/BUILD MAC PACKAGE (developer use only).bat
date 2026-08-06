@echo off
title MBC2 Dashboard - Build Mac Package
REM ================================================================
REM  Builds dist\MBC2Dashboard-Mac-<ver>.zip - the Mac package:
REM    Start MBC2 Dashboard.command + app/ source + Mac README
REM
REM  Runs on Windows (it only stages files and zips them).
REM  NOTE: Mac users need "chmod +x" on the .command after unzipping
REM  if zip strips the execute bit - covered in the Mac README.
REM  Version comes from VERSION.
REM ================================================================
setlocal
cd /d "%~dp0.."
set /p APPVERSION=<app\VERSION
echo.
echo  Building Mac package v%APPVERSION% ...

set STAGE=dist\mac-stage\MBC2Dashboard
if exist "dist\mac-stage" rmdir /s /q "dist\mac-stage"
mkdir "%STAGE%\app"

copy /y "mac\Start MBC2 Dashboard.command"  "%STAGE%\"      >nul
copy /y "mac\README.txt"                    "%STAGE%\"      >nul
copy /y "app\server.py"                     "%STAGE%\app\"  >nul
copy /y "app\db_manager.py"                 "%STAGE%\app\"  >nul
copy /y "app\motor_api.py"                  "%STAGE%\app\"  >nul
copy /y "app\mbc2-dashboard.html"           "%STAGE%\app\"  >nul
copy /y "app\schema.sql"                    "%STAGE%\app\"  >nul
copy /y "app\default_programs.json"         "%STAGE%\app\"  >nul
copy /y "app\VERSION"                       "%STAGE%\app\"  >nul
copy /y "requirements.txt"                  "%STAGE%\"      >nul

powershell -Command "Compress-Archive -Force -Path 'dist\mac-stage\MBC2Dashboard' -DestinationPath 'dist\MBC2Dashboard-Mac-%APPVERSION%.zip'"
rmdir /s /q "dist\mac-stage"

if not exist "dist\MBC2Dashboard-Mac-%APPVERSION%.zip" (
    echo  BUILD FAILED.
    pause
    exit /b 1
)

echo.
echo  ==========================================
echo   Done: dist\MBC2Dashboard-Mac-%APPVERSION%.zip
echo  ==========================================
echo.
pause
