MBC2 DASHBOARD - WINDOWS PORTABLE / USB EDITION
================================================

WHAT'S IN THIS PACKAGE
-----------------------
  MBC2Dashboard.exe          <- the application
  Start MBC2 (USB).bat       <- launch with data stored on THIS stick
  Start MBC2 (this PC).bat   <- launch with data stored on this PC
  README.txt                 <- this file

HOW TO LAUNCH
-------------
Double-click one of the launcher .bat files - NOT the exe directly:

  Start MBC2 (USB).bat
    Sessions and backups are saved to a "data" folder ON THIS STICK.
    Plug the stick into any Windows PC and your history travels with it.

  Start MBC2 (this PC).bat
    Sessions are saved to your PC's standard data folder:
    %LOCALAPPDATA%\MBC2Dashboard\

REQUIREMENTS
------------
1. CH340 DRIVER - the MBC2 uses a CH340 USB-to-serial chip.
   Download: https://www.wch-ic.com/downloads/CH341SER_EXE.html

   ARM64 USERS (Surface Pro X, Copilot+ PCs): install exactly
   v3.9.2024.9 - newer versions dropped ARM64 support.

   No browser is needed. The dashboard runs in its own window.

CONNECTING TO THE MBC2
----------------------
Plug the MBC2 in, pick its COM port from the dropdown at the top of
the window, then click "Connect MBC2". Use the refresh button next
to the dropdown if you plugged the device in after starting the app.

SMARTSCREEN WARNING
-------------------
Windows may warn "Windows protected your PC" on first run.
Click "More info" -> "Run anyway" to proceed.

WHERE IS MY DATA?
-----------------
  USB mode:    data\mbc2.db  (beside this exe, on the stick)
  PC mode:     %LOCALAPPDATA%\MBC2Dashboard\mbc2.db
  Backups:     ...\MBC2Dashboard\backups\  (auto, last 14 days)
