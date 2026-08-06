MBC2 DASHBOARD - MAC
====================

*** PLEASE NOTE: the Mac version is currently UNTESTED.
*** The developers run Windows. The core app is the same, but
*** expect rough edges. Please report problems via GitHub.
*** The Windows version is the recommended experience.

WHAT'S IN THIS PACKAGE
-----------------------
  Start MBC2 Dashboard.command   <- double-click this to run
  app/                           <- the application files
  requirements.txt               <- Python packages needed
  README.txt                     <- this file

REQUIREMENTS
------------
1. Python 3 - modern Macs usually have it. If not:
   https://www.python.org/downloads/

2. The pyserial package - REQUIRED to talk to the MBC2. Install it
   by opening Terminal and running:

      python3 -m pip install --user pyserial

   The launcher checks for this and will tell you if it is missing.
   Without it the dashboard opens but cannot connect to the device.

3. A web browser - Chrome or Edge are what we test. Safari and
   Firefox should also work now that serial runs in Python rather
   than the browser, but they are untested.

4. CH340 driver - needed for the MBC2 USB connection.
   Mac driver: https://www.wch-ic.com/downloads/CH341SER_MAC_ZIP.html

FIRST RUN
---------
1. Right-click "Start MBC2 Dashboard.command" -> Open -> Open
   (one-off macOS security approval; after that just double-click).

2. If macOS says it cannot be executed, open Terminal and run:
      chmod +x "Start MBC2 Dashboard.command"

3. The app opens in your browser on http://127.0.0.1:8766
   Connect the MBC2 via USB, choose its port from the dropdown at
   the top of the page (it will look like /dev/tty.usbserial-XXXX
   or /dev/tty.wchusbserialXXXX), then click "Connect MBC2".

WHERE IS MY DATA?
-----------------
~/Library/Application Support/MBC2Dashboard/
(mbc2.db + server.log + backups/ - automatic daily backups, 14 days)

Data lives outside this folder, so replacing the app with a newer
package never touches it.
