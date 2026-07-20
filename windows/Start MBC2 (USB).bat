@echo off
REM Launches MBC2 Dashboard with session data stored on THIS USB stick.
REM Sessions, logs and backups are saved to a "data" folder beside this file.
setlocal
set MBC2_DATA_DIR=%~dp0data
start "" "%~dp0MBC2Dashboard.exe"
