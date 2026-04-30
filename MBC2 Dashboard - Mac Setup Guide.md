# MBC2 Dashboard — Mac Setup Guide

Everything you need to get the MBC2 Dashboard running on a Mac, step by step.

---

## What you need

- A Mac running macOS 10.15 (Catalina) or later
- Google Chrome or Microsoft Edge browser
- Python 3 (instructions below if you don't have it)
- The MBC2 Dashboard folder

---

## Step 1 — Install the CH340 USB driver

The MBC2 connects via a CH340 USB chip. Macs don't include this driver by default so you need to install it once.

1. Go to: **https://www.wch-ic.com/downloads/CH341SER_MAC_ZIP.html**
2. Download the ZIP file and open it
3. Run the `.pkg` installer inside
4. When macOS asks, go to **System Settings → Privacy & Security** and click **Allow** next to the blocked driver notice
5. **Restart your Mac**

> If you're on macOS Sonoma or Ventura, the Privacy & Security step is required — the driver won't work without it.

---

## Step 2 — Check Python is installed

Open **Terminal** (search for it in Spotlight with `Cmd + Space`) and type:

```
python3 --version
```

If you see a version number (e.g. `Python 3.11.4`) you're good — skip to Step 3.

If you get an error or a prompt to install developer tools:

1. Go to **https://python.org/downloads**
2. Download the latest version for macOS and run the installer
3. Reopen Terminal and run `python3 --version` again to confirm

> **Note about the zsh message:** If Terminal shows a message saying *"The default interactive shell is now zsh"*, that's normal on modern Macs — it's not an error. You can either ignore it or run `chsh -s /bin/zsh` to switch to zsh and stop seeing it. Neither option affects the dashboard.

---

## Step 3 — Prepare the launcher to run

Two things need to happen before the launcher will work. Do both before trying to run it.

### 3a — Allow through Gatekeeper (required on first launch)

Because the file was downloaded from the internet, macOS will block it the first time:

1. In Finder, locate **`Start MBC2 Dashboard.command`** in the MBC2 Dashboard folder
2. **Right-click** the file and select **Open**
3. A warning will appear saying the file is from an unidentified developer — click **Open** anyway

> After the first launch, you can double-click it normally. If the file just opens as a text document instead of running, complete Step 3b first.

### 3b — Set execute permission (if the launcher opens as text instead of running)

Downloaded files on Mac sometimes don't have execute permission. If double-clicking the launcher just shows its contents as text, fix it like this:

1. Open **Terminal** (Cmd + Space → type Terminal → Enter)
2. If you see the zsh message, just press Enter to dismiss it
3. Navigate to the MBC2 Dashboard folder — the easiest way is to type `cd ` (with a space after it), then drag the **MBC2 Dashboard folder** from Finder into the Terminal window, then press Enter
4. Run this command exactly as shown:

```
chmod +x "Start MBC2 Dashboard.command"
```

5. Press **Enter** — no output means it worked
6. Go back to Step 3a and right-click → Open the launcher

You only need to do this once.

---

## Step 4 — Connect the MBC2

1. Plug the MBC2 into your Mac via USB
2. The MBC2 should power on
3. Wait a few seconds for macOS to recognise the device

---

## Step 5 — Open the dashboard

1. Double-click **`Start MBC2 Dashboard.command`**
2. A Terminal window opens — leave it running in the background
3. Chrome or Edge should open automatically at **http://localhost:8766**
4. If the browser doesn't open, type `http://localhost:8766` into Chrome or Edge manually

> **Important:** Use Chrome or Edge only. Safari and Firefox do not support the Web Serial API that connects to the MBC2.

---

## Step 6 — Connect to the MBC2

1. In the dashboard, click **Connect** in the top left
2. A browser popup will appear listing available serial ports
3. Look for a port with a name like:
   - `cu.usbserial-XXXXXXXX`
   - `cu.wchusbserial_XXXXXXXX`
4. Select it and click **Connect**

> Always use the `cu.` version if you see both `cu.` and `tty.` for the same device — the `tty.` variant can cause connection issues on Mac.

The dashboard will start showing live data as soon as the MBC2 begins a session.

---

## Stopping the dashboard

1. Click **Stop Server** inside the dashboard (preferred)
2. Then close the Terminal window

> Closing the Terminal window without stopping the server first can leave a background process running on some macOS versions. If the dashboard won't start next time, restart your Mac to clear it.

---

## Troubleshooting

**No ports appear in the connect popup**
- Check the CH340 driver is installed and the Mac has been restarted (Step 1)
- Try a different USB cable — some cables are charge-only and have no data lines
- Unplug and replug the MBC2 then try connecting again

**Port appears but no data comes through**
- Make sure the MBC2 is powered on and running or at the menu screen
- Confirm the baud rate is 115200 (this is set automatically by the dashboard)

**Terminal window closes immediately after launching**
- Python is not installed — follow Step 2
- Try running the server manually: open Terminal, navigate to the MBC2 Dashboard folder (drag it in after typing `cd `), then run `python3 server.py`

**Dashboard opens but shows an orange warning banner**
- You opened `mbc2-dashboard.html` directly instead of using the launcher
- Close the tab, run the launcher again, and use **http://localhost:8766**

**The launcher opens as a text file instead of running**
- Execute permission is not set — follow Step 3b

**"Syntax error near unexpected token" appears in Terminal**
- You have extra characters around the file path — run the chmod command exactly as shown in Step 3b, with the filename in quotes

---

## Summary — quick start checklist

- [ ] CH340 driver installed and Mac restarted
- [ ] Python 3 installed
- [ ] Launcher allowed through Gatekeeper (right-click → Open, first time only)
- [ ] Execute permission set if needed (`chmod +x "Start MBC2 Dashboard.command"`)
- [ ] MBC2 plugged in via USB
- [ ] Dashboard opened in **Chrome or Edge** (not Safari or Firefox)
- [ ] Connected to `cu.usbserial-XXXX` or `cu.wchusbserial-XXXX` port
