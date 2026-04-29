# Changelog

All notable changes to MBC2 Dashboard are documented here.

---

## [3.0.0] — 2026-04-30

### Architecture — DB-only storage

All session and program data is now stored exclusively in `mbc2.db`. The `data/sessions/` CSV folder and `data/programs.json` file are no longer used. This eliminates the data loss issue caused by path resolution differences between launch locations and the fragile timestamp-based CSV matching that was used to retrieve session data.

### Breaking changes

- `POST /api/sessions` payload changed — now accepts `{ motor_id, session_type, notes, rows: [...] }` with parsed row objects instead of a CSV string. All session rows are written directly to the `session_data` table.
- `GET /api/sessions` now returns an array of session objects from the DB (with motor, peak RPM, row count) instead of a list of CSV filenames.
- `GET /api/sessions/<id>/data` — new endpoint, returns session rows from the DB by session ID.
- `GET /api/sessions/<id>/export` — new endpoint, generates a CSV on demand from DB rows for Excel export.
- `DELETE /api/sessions/<id>` — now accepts a numeric session ID (was a filename string).
- `GET /api/programs` and `POST /api/programs` (JSON file endpoints) removed. Program library is read and written via `/api/profiles` and `/api/profiles/import` exclusively.

### server.py

- Removed all `DATA_DIR`, `sessions_dir`, and `programs.json` file handling.
- `POST /api/sessions` writes rows to `session_data` table and optionally records a benchmark and break-in log entry in the same request.
- `GET /api/sessions` returns DB session list.
- `GET /api/sessions/<id>/export` streams a CSV generated from the DB.
- `DELETE /api/sessions/<id>` cascades deletion through `session_data`, `benchmarks`, and `motor_breakin_log`.
- Seed file lookup simplified — looks in app root only, no `data/` subfolder search.

### db_manager.py

- `DB_PATH` now uses `Path(__file__).resolve().parent` — database is always found relative to the script file regardless of the working directory Python is launched from. This was the root cause of the data disappearing between sessions.
- Added `get_all_sessions()` — returns all sessions with motor identifier, model, peak RPM, benchmark type, and row count.
- Added `delete_session(session_id)` — cascades through `session_data`, `benchmarks`, and `motor_breakin_log`.
- Added `export_session_csv(session_id)` — generates a CSV string from `session_data` rows on demand, no file written to disk.
- Added `parse_mbc2_row(raw_line, session_id, timestamp_ms)` — parses a raw MBC2 serial CSV line into a `session_data` row dict. Available for use if raw line ingestion is added in future.

### motor_api.py

- Removed duplicate fuzzy timestamp CSV matching block. Session data retrieval now goes directly to the DB via `db.get_session_data()`.

### mbc2-dashboard.html

- `autoSaveSession()` — maps `sessionData` rows to DB field format and POSTs the full row array to `POST /api/sessions`. No CSV file is created.
- `saveSessionCSV()` — when a `session_id` exists, triggers a download from `/api/sessions/<id>/export` instead of building a CSV in-browser from memory.
- `deleteSession()` — uses the numeric `session_id` stored on the session object instead of deriving a filename.
- `loadLibrary()` — reads from `GET /api/profiles` (DB). DB field names (`profile_id`, `mbc2_label`, `duration_sec`, etc.) normalised to UI field names on load.
- `saveLibrary()` — posts to `POST /api/profiles/import` (DB) instead of `POST /api/programs` (JSON file).
- `loadServerSessions()` — reads session index from `GET /api/sessions`. Returns metadata (motor, peak RPM, row count) immediately; rows are not fetched until a session is opened.
- `loadSessionIntoView()` — now `async`. Fetches rows from `GET /api/sessions/<id>/data` on first open if not already in memory. Normalises DB field names back to UI format.
- `renderSessionList()` — session chips now display motor identifier and peak RPM from DB metadata.
- Comparison chart updated to use `GET /api/sessions/<id>/data` instead of the old motor-scoped session data route.

---

## Prior development history

This repo starts at v3.0.0. The following is a condensed summary of the development that took place in the previous repository before the architecture was stable enough to version properly.

**v0.4.0 — 2026-04-26**
Target RPM reference line on live chart. kV curve in benchmark results panel. Motor comparison side-by-side stats table and RPM overlay for up to 5 sessions. Session notes and ambient temperature fields. Per-step cooldown timer in sidebar. Pre-treatment structured dropdown replacing freetext field. Twelve bug fixes covering PRO motor direction lock, program DB ID resolution, duplicate payload keys, dropdown visibility sync, motor detail view, session chip JS escaping, roster sort indicators, filename sanitiser, and benchmark kV display.

**v0.3.0 — 2026-04-24**
SQLite motor registry database introduced (`mbc2.db`). Motors tab added alongside Charts and Raw Data. Motor registration with auto-generated identifiers (`SD-R-01` format). Full Tamiya motor lineup and chassis assignment. Break-in program linking. Motor registry view with session count and best peak RPM. Full API route set for motors and profiles. Database schema covering 11 tables: mount types, chassis, motor models, motors, chassis assignments, profiles, programs, program steps, break-in log, sessions, session data, and benchmarks.

**v0.2.0 — 2026-04-23**
Moved to server-based architecture (`server.py` on port 8766). Program library drawer with full profile and program CRUD. MBC2 Entry Guide modal. Active program selector with persistence. Firmware version checker. Session CSV save. Windows and Mac launchers. Program library backed by `data/programs.json` with localStorage fallback. Sessions saved as CSV files in `data/sessions/`.

**v0.1.0–v0.1.2 — 2026-04-23**
Initial build. Web Serial API connection to MBC2 at 115200 baud. Live RPM, Amps, Voltage, kV efficiency, and Temperature charts. Session recording. Serial column mapping confirmed from live capture. Temperature −273°C sensor-disconnect handling. Firmware panel added.
