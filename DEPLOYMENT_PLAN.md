# MBC2 Dashboard — v4 Packaging & Deployment Plan

*Created: 2026-07-20 · Branch: `v4-packaging` · Status: Phases 1–4.7 complete —
artefacts rebuilt 2026-08-06; Phase 5 test matrix is all that remains*

Modelled on the Tamiya Race Manager v10 packaging plan; reuses its build
machinery (PyInstaller spec, Inno Setup script, build bats, Mac zip builder,
`app`/`windows`/`mac` repo layout) with MBC2-specific changes noted throughout.

---

## Goals

1. **One-click install on Windows** — a single installer with a desktop icon.
   No Python download, no bat files, no zip juggling.
2. **Updates can never damage the motor database.** `mbc2.db` and the app are
   physically separated so an installer cannot touch session data, by
   construction.
3. **Backups happen automatically.** A user who never backs up is still
   protected.
4. **USB standalone mode** — exe + data on a stick; sessions travel with the
   stick between machines.
5. **Mac package** — launcher + source zip (built on Windows, same as TRM).
6. `main` stays the stable v3.4 line until the packaging branch is proven.

## Non-goals (explicit)

- **No driver installation.** The CH340 driver cannot and should not be
  silently installed by our packages. Documentation + a download link (and
  optionally the driver installer dropped onto prepared USB sticks) is the
  approach. The ARM64 driver pin (v3.9.2024.9) stays documentation-only.
- **No code signing** for now (cost). SmartScreen click-through is documented
  instead, same as TRM.

> **Architecture update (pywebview):** The original "no native window" verdict
> was because WebView2 lacks Web Serial API support. This is resolved: serial
> has moved to Python (pyserial), streamed to the frontend via SSE. The exe now
> runs in a pywebview native window — no Chrome dependency at runtime.

---

## Branch strategy

| Branch | Purpose |
|---|---|
| `main` | Stable v3.4 — only critical fixes until merge. |
| `v4-packaging` | All work in this plan. Merged to `main` only after the test matrix passes. |

Tag `v3.4` on `main` before starting so the last pre-packaging version is
always recoverable.

---

## Architecture changes (the core of the safety guarantee)

### 1. Data moves out of the app folder

| | Location |
|---|---|
| App (replaceable) | `%LOCALAPPDATA%\Programs\MBC2Dashboard\` (installer) or wherever the exe sits (portable) |
| Data (never touched by installer) | `%LOCALAPPDATA%\MBC2Dashboard\mbc2.db` |
| Backups | `%LOCALAPPDATA%\MBC2Dashboard\backups\` |
| Log | `%LOCALAPPDATA%\MBC2Dashboard\server.log` |

- Mac: `~/Library/Application Support/MBC2Dashboard/`.
- **`MBC2_DATA_DIR` env var overrides everything** — this is the USB mode
  mechanism (launcher bat sets it to a `data` folder next to the exe).
- `db_manager.DB_PATH` derives from the resolved data dir; the SQLite
  `-wal`/`-shm` siblings follow automatically.

**One-time migration on first launch of v4:** if a legacy `mbc2.db` exists
next to the app and the new location has no database, it is **copied**
(never moved) to the new home; a `DATA-HAS-MOVED.txt` note is left behind
and the app shows a one-time notice. The original stays in place as a
fossil backup.

### 2. Automatic rolling backups (SQLite-specific)

- On every server **startup**, before any connection is opened for serving:
  back up the DB to `backups/mbc2-YYYY-MM-DD.db` (first launch of the day
  only — preserves yesterday's final state). Keep the most recent 14, prune
  older.
- Use `sqlite3.Connection.backup()` rather than a file copy, so a WAL left
  by a crashed previous run is checkpointed correctly into the backup.
- The existing on-demand CSV export stays as the per-session export path.

### 3. Schema migrations — already in place

Unlike TRM, the schema layer already auto-migrates: `CREATE TABLE IF NOT
EXISTS` everywhere plus `_add_column_if_missing()` for new columns, running
against any existing DB on launch. No new framework needed. Rules stay as in
CLAUDE.md: never drop or rename columns.

### 4. Version single-sourcing

- New `app/VERSION` file is the single source of truth.
- Served via a new `GET /api/info` (version + data dir path); the dashboard
  footer reads it on load (replaces the hand-edited footer string).
- Build scripts read `VERSION` for installer/zip filenames, same as TRM.

---

## Packaging specifics

### Windows exe (PyInstaller, onefile)

- Entry point stays `server.py` (no separate `app.py` — there is no native
  window). `console=False`; prints go to `server.log` in the data dir.
- Bundled data files: `mbc2-dashboard.html`, `schema.sql`,
  `default_programs.json`, `VERSION`, `icon.ico`.
- Browser opens **only after the socket is bound** (replaces the current
  0.8 s timer).
- Port 8766 conflict handling: if `/api/ping` answers, an instance is
  already running → just open the browser to it and exit. A foreign program
  on the port → plain-English message box (ctypes `MessageBoxW`), no
  traceback.
- **Build with x64 Python.** The dev machine is ARM64 (Surface X); an
  ARM64-Python build produces an exe other members' x64 machines can't run.
  x64 Python runs fine under emulation. Record the exact interpreter in
  `BUILD.md`.
- Icon: Kris supplies artwork (as with TRM); generated to multi-size
  `app/icon.ico` with Pillow.

### Windows installer (Inno Setup)

- Copy-adapt `TamiyaRaceManager.iss`: per-user
  (`PrivilegesRequired=lowest`), desktop icon (default on), Start Menu
  entry, uninstaller.
- Installer asks a running instance to shut down first (existing
  `GET /api/shutdown`).
- Pre-install info page covers: data lives separately and is never touched
  by install/update/uninstall; **Chrome or Edge is required** (Web Serial);
  **CH340 driver required** with download link and the ARM64 v3.9.2024.9
  pin; SmartScreen click-through.

### USB / portable package

Zip containing:

```
MBC2Dashboard.exe
Start MBC2 (USB).bat        ← sets MBC2_DATA_DIR=%~dp0data, starts exe
Start MBC2 (this PC).bat    ← starts exe with default data home (optional)
README.txt                  ← Chrome + CH340 requirements, how data-on-stick works
```

- First USB launch creates `data\mbc2.db` on the stick; sessions and
  backups live there and travel with it.
- Host machine still needs Chrome/Edge and the CH340 driver — stated
  loudly in the README. Kris may drop the CH340 installer onto sticks he
  prepares personally (we link rather than redistribute in the published
  zip).

### Mac package

- Zip: `Start MBC2 Dashboard.command` (adapted from the existing one) +
  `app/` source + Mac README. Requires python3 (preinstalled/CLT) and
  Chrome; Mac CH340 driver note.
- Built on Windows by `mac\BUILD MAC PACKAGE (developer use only).bat`
  (copy-adapt from TRM). Ships with an UNTESTED disclaimer unless a real
  Mac test happens first.

---

## Repo restructure (Phase 4, via `git mv` — history preserved)

```
app/        server.py, db_manager.py, motor_api.py, mbc2-dashboard.html,
            schema.sql, default_programs.json, VERSION, icon.ico
windows/    MBC2Dashboard.iss, BUILD EXE.bat, BUILD INSTALLER.bat, README.txt,
            installer-info.txt
mac/        Start MBC2 Dashboard.command, BUILD MAC PACKAGE.bat, README.txt
docs/       unchanged (SERIAL_SPEC.md, DB_SCHEMA.md, etc.)
```

- Root `README.md` rewritten as a platform picker (Windows installer /
  USB zip / Mac zip / run from source).
- Absorbed and removed: `START MBC2 DASHBOARD.bat`,
  `Start MBC2 Dashboard.command` (root copy), both `MBC2 Dashboard - *
  Setup Guide.md` files → their content moves into per-platform READMEs.
- `.gitignore` gains `build/`, `dist/`.
- `CLAUDE.md` updated: new paths, packaging facts, and the no-native-window
  decision recorded as a hard rule (Web Serial).
- **Christchurch rule restated for packages:** `default_programs.json`
  ships inside every artefact and must never contain PMPE/SPRF. The
  private `christchurch_protocol.json` is never bundled; it remains a
  separately-distributed import. A USB stick prepared for a club member
  may contain a DB with imported club programs — that is fine (private
  distribution), but the *published* zips must be built from a clean
  checkout, never from a working folder with a live DB.

---

## Work phases

### Phase 1 — Data home, backups, version (server-side; no packaging yet) ✓ COMPLETE
- [x] Data-dir resolution: `MBC2_DATA_DIR` → platform default; create on
      first run.
- [x] `db_manager.DB_PATH` derives from data dir; `schema.sql` and
      `default_programs.json` located relative to the app bundle (PyInstaller
      `_MEIPASS`-aware helper).
- [x] Legacy `mbc2.db` copy-never-move migration + `DATA-HAS-MOVED.txt` +
      one-time in-app notice (via `/api/info`).
- [x] Startup rolling backup (sqlite backup API, keep 14, daily).
- [x] `VERSION` file, `/api/info`, footer reads version dynamically.
- [x] Server log to file when frozen (`sys.frozen`), console when from source.

### Phase 2 — Single executable
- [x] Confirm WebView2 Web Serial verdict: **unsupported.** Resolution: serial
      moved to Python (pyserial + SSE); app opens in pywebview native window.
- [x] PyInstaller spec (`MBC2Dashboard.spec`) + `windows\BUILD EXE
      (developer use only).bat` (x64 Python; see `BUILD.md`).
- [x] Browser-after-bind; already-running guard; foreign-port message box
      (completed in Phase 1).
- [x] Icon artwork: `icon.ico` generated (16/32/48/64/128/256 px) from
      `icon/icon.png`. Moves to `app/icon.ico` in Phase 4 restructure.
- [x] Smoke test passed (2026-07-20, Python 3.14.4 x64, PyInstaller 6.21.0):
      fresh launch → `/api/info` returns `{version:4.0}`; legacy migration →
      db copied, `DATA-HAS-MOVED.txt` written, original untouched; shutdown →
      process exits code 0, port 8766 released.

### Phase 3 — Packages ✓ COMPLETE
- [x] `windows\MBC2Dashboard.iss` + `BUILD INSTALLER (developer use only).bat`
      → `dist\installer\MBC2Dashboard-Setup-4.0.exe` (11.5 MB) built OK.
- [x] USB launcher bats (`Start MBC2 (USB).bat`, `Start MBC2 (this PC).bat`)
      + `windows\README.txt`
      → `dist\MBC2Dashboard-WindowsPortable-4.0.zip` (9.4 MB) built OK.
- [x] `mac\` package + `BUILD MAC PACKAGE (developer use only).bat`
      → `dist\MBC2Dashboard-Mac-4.0.zip` (0.1 MB) built OK.
- [x] Installer info page (`windows\installer-info.txt`) and per-platform
      READMEs (`windows\README.txt`, `mac\README.txt`) with Chrome + CH340
      + ARM64 driver pin + SmartScreen click-through notes.

### Phase 4.5 — pywebview + server-side serial
- [x] Serial moved to Python: `SerialManager` class in `app/server.py`;
      `/api/ports`, `/api/serial/connect`, `/api/serial/disconnect`,
      `/api/serial/send`, `/api/serial/stream` (SSE) routes added.
- [x] Frontend rewritten: Web Serial API removed; port selector dropdown +
      ⟳ refresh button; `connectSerial` / `disconnectSerial` / `sendCommand`
      use HTTP + SSE; all stale `port` variable references updated.
- [x] `app/app.py` created: pywebview entry point; starts server in background
      thread, polls `/api/ping`, opens native window; window-close → `os._exit`.
- [x] `app/splash.png` generated: 400×400 px from `app/icon/icon.png`.
- [x] `MBC2Dashboard.spec` updated: entry point → `app/app.py`; `collect_all('webview')`
      binaries/datas/hiddenimports; `Splash('app/splash.png', ...)` block.
- [x] Build test passed (2026-07-20, Python 3.14.4 AMD64, PyInstaller 6.21.0,
      pywebview 6.2.1, pyserial 3.5): native window opens; `/api/ping` → 200;
      `/api/shutdown` → clean exit (code 0) within ~4s.

### Phase 4 — Repo restructure & docs ✓ COMPLETE
- [x] `git mv` into `app/`; `windows/` and `mac/` already in place; paths
      fixed in spec, bats, iss.
- [x] Root README rewritten as platform picker; old setup guides removed;
      root launchers removed.
- [x] `BUILD.md` expanded: clean-checkout guide, x64-Python note, ASCII-bat
      gotcha, dist verification checklist.
- [x] `CLAUDE.md` updated: v4.0, new repo layout, no-native-window hard rule.
      `docs/VERSION_HISTORY.md` v4.0 entry added.
- [x] `RELEASE_NOTES_v4.md` drafted: upgrade paths, SmartScreen note (TODO:
      screenshot), CH340/ARM64 pin, compatibility policy.

### Phase 4.6 — Docs caught up with 4.5 (2026-08-06) ✓ COMPLETE

Phase 4.5 changed the architecture but only touched code, the spec, `BUILD.md`
and this plan — every user-facing document still promised a Chrome-based app.

- [x] `CLAUDE.md`: stack table, repo layout, and hard rules rewritten. The
      "no native window — ever" rule is withdrawn and replaced with
      "serial belongs in Python" + "two entry points, keep them in sync".
- [x] `README.md`, `windows/README.txt`, `windows/installer-info.txt`,
      `mac/README.txt`, `RELEASE_NOTES_v4.md`: Chrome requirement removed for
      Windows packages; COM-port dropdown flow documented; WebView2 note added.
- [x] `CHANGELOG.md`: v4.0 entry written.
- [x] `requirements.txt` added (pyserial); Mac launcher warns when it's
      missing; Mac build bat ships it. Closes the 4.5 gap where the Mac
      package could not connect at all.
- [x] Two frontend bugs found while checking the docs' claims, both fixed:
      the `'serial' in navigator` guard disabled Connect inside the native
      window, and the no-ports banner was reset to its CSS `display:none`
      instead of being shown.
- [x] Risks table and matrix rows 1, 5, 6, 11 updated for the new architecture.

### Phase 4.7 — Rebuild artefacts (2026-08-06) ✓ COMPLETE

`dist/` had held pre-4.5 builds (15:50–15:51 on 2026-07-20, before the 19:32
pywebview commit) that still shipped the browser-based app. All three rebuilt
from a clean clone of `0935ce1`, Python 3.14.4 AMD64 / PyInstaller 6.21.0:

| Artefact | Was | Now |
|---|---|---|
| `MBC2Dashboard-Setup-4.0.exe` | 11.5 MB | 23.0 MB |
| `MBC2Dashboard-WindowsPortable-4.0.zip` | 9.4 MB | 21.0 MB |
| `MBC2Dashboard-Mac-4.0.zip` | 0.08 MB | 0.08 MB (+ `requirements.txt`) |

Verified: exe is x64 (PE machine `0x8664`); zip contents match the `BUILD.md`
checklist; no `.db` anywhere in `dist/` or inside either zip; no PMPE/SPRF in
the bundled `default_programs.json`; the Mac `.command` kept LF endings
through a clean checkout (the `.gitattributes` fix working as intended).

Exe smoke test with `MBC2_DATA_DIR` pointed at a scratch folder: fresh DB
created, motor models + 6 profiles seeded, daily backup written, `/api/info`
returned `{"version":"4.0"}`, page and `/api/ping` returned 200, `/api/ports`
returned `[]` (no device attached), `/api/shutdown` released the port with no
orphaned process. **Covers matrix rows 1 and 4, and row 10 for the HTTP
shutdown path.**

**Native window verified 2026-08-06** by screen capture of the running exe:
process exposes a real window handle titled `MBC2 Dashboard v4.0` at 1400×900,
with the dashboard fully rendered under WebView2. Both Phase 4.6 frontend fixes
confirmed in the real environment — Connect MBC2 is enabled (it would have been
permanently disabled by the old `navigator.serial` guard) and the "no COM ports
found" banner displays. Row 1 complete. Toolbar clipping at the default window
size logged in `docs/FEATURE_ROADMAP.md` as UI polish.

Still needs hardware or a person: rows 7–9, 11, 12, 13.

⚠ On the windowed build `/api/shutdown` may return no HTTP response (curl
reports `000`) because the process exits before flushing it. The port is
released and no process is orphaned, so this is expected — do not read a
missing 200 as a row 10 failure.

### Phase 5 — Test matrix & release
See matrix below. Then: merge → `main`, tag `v4.0`, GitHub release with all
three artefacts attached.

---

## Test matrix (all must pass before merge)

| # | Scenario | Expected | Who |
|---|---|---|---|
| 1 | Fresh install, no prior data | Empty DB created in new home, motor models seeded, **native window opens** (no browser launched) | ✓ **PASSED** 2026-08-06 |
| 2 | Exe run from inside old v3.x folder (legacy `mbc2.db` beside it) | Data copied to new home, original untouched (hash-verified), moved-note written, one-time notice shown | scripted |
| 3 | Installer over installer (update) | App files replaced; DB + backups untouched (hash + mtime) | scripted |
| 4 | Daily backup | First launch of day creates `backups/mbc2-<date>.db`; 15th day prunes oldest | scripted |
| 5 | Port 8766 in use by running instance | Second exe opens a **pywebview window onto the existing instance** and starts no second server (`app.py:60`, `srv._already_running()`) | scripted |
| 6 | Port 8766 in use by foreign program | Friendly message box, no traceback, no window (`app.py:72`) | scripted |
| 7 | USB mode on a second machine | DB created/used on stick; sessions persist across machines | 🧑 KRIS |
| 8 | Hardware: connect MBC2, record break-in on packaged exe | Rows land in DB (session chip row count), CSV export has data | 🧑 KRIS |
| 9 | Hardware: benchmark flow + Read All Settings + program slot read | Benchmark saved; settings grid loads; slot display renders | 🧑 KRIS |
| 10 | Stop Server button on packaged exe | Server exits, no orphaned process in Task Manager | 🧑 KRIS |
| 11 | **Window** close mid-recording (packaged exe) | Connection record closed with `end_reason=tab_closed`. ⚠ **Expected to fail** — `app.py:89` calls `os._exit(0)` on window close, which may kill the process before the `pagehide` beacon is served. Verify; if it fails, close the connection server-side on shutdown instead. | 🧑 KRIS |
| 11b | Tab close mid-recording (source/Mac, browser) | beforeunload warning; connection record closed (`end_reason=tab_closed`) | scripted |
| 12 | Mac package on a real Mac | `pyserial` warning shown if absent; launches, serves, connects (or ships with UNTESTED disclaimer) | 🧑 KRIS / disclaimer |
| 13 | SmartScreen click-through on a machine that hasn't seen the exe | Screenshots captured for release notes | 🧑 KRIS |

---

## Known risks — advertised, with instructions

| Risk | Who is affected | Mitigation / instruction |
|---|---|---|
| ~~Chrome/Edge required~~ — **resolved by Phase 4.5.** Serial is server-side; Windows packages run in a pywebview window and need no browser. | — | Docs updated 2026-08-06. Remaining browser dependency is source/Mac only, where any modern browser works. |
| **WebView2 runtime required on Windows.** pywebview uses it; absent on very old/unpatched Windows 10. | Windows 10 machines that have never updated | Noted in `installer-info.txt`. Present by default on Win11 and current Win10. Not yet verified on a machine without it — worth a test-matrix row if one is available. |
| **`pyserial` required from source and on Mac.** Without it the app runs but cannot connect. | Mac users, source users | `requirements.txt` added; Mac launcher checks and warns; both READMEs give the pip command. |
| **CH340 driver required; ARM64 machines need exactly v3.9.2024.9.** No installer may touch drivers. | Everyone; ARM64 users especially | Download link + ARM64 pin in READMEs and installer page; Kris may pre-load the driver on sticks he hands out. |
| **Zip → installer upgrades don't auto-migrate** (installed exe can't see the old folder). Data is safe but looks lost. | v3.x users moving to the installer | Same TRM playbook: first-run hint + info page → run the new exe once *from the old folder* (auto-migrates), or copy `mbc2.db` into the new data home. |
| SmartScreen warning on unsigned exe | All new installs | Documented click-through with screenshots; signing deferred (cost). |
| ARM64-built exe won't run on x64 machines | Anyone Kris shares the exe with | Build with x64 Python only; `BUILD.md` states this in bold. |
| Published USB zip accidentally containing a live DB with club programs | Christchurch club privacy | Packages are built from a clean checkout by script; `dist/` output verified to contain no `.db`; rule restated in `BUILD.md`. |

## Compatibility policy (plain English, for release notes)

- **Old databases into a new app: always works.** The schema auto-migrates
  forward on launch and columns are never dropped.
- **New databases into an old app: unsupported.** v3.x has no version gate;
  release notes say don't do it. The startup backup is the recovery path.
- **CSV export remains the universal per-session interchange format**; the
  DB file itself is the whole-history transfer format (copy it into the
  data home of any equal-or-newer version).
