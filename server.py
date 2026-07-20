#!/usr/bin/env python3
"""
MBC2 Dashboard Server
- Serves mbc2-dashboard.html
- Data lives in a dedicated data directory (separate from the app)
- Auto-migrates legacy mbc2.db from beside-the-exe on first v4 launch
- Rolling daily backups (14 kept, sqlite3 backup API)
- Opens browser after server is bound
- Shuts down via Stop Server button or Ctrl+C
"""

import http.server
import json
import logging
import os
import shutil
import socketserver
import sqlite3
import sys
import threading
import time
import webbrowser
from pathlib import Path

PORT = 8766

# ── Resource and app dirs ──────────────────────────────────────────────────────
# When frozen (PyInstaller onefile): bundled files unpack to sys._MEIPASS;
# the exe itself sits at sys.executable's parent.
# When running from source: both are this file's parent.
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).parent
else:
    RESOURCE_DIR = APP_DIR = Path(__file__).parent

try:
    APP_VERSION = (RESOURCE_DIR / 'VERSION').read_text(encoding='utf-8').strip()
except Exception:
    APP_VERSION = '?'

# ── Data directory ─────────────────────────────────────────────────────────────
def _resolve_data_dir() -> Path:
    """Motor data lives outside the app folder so updates can never touch it.
    MBC2_DATA_DIR env var overrides everything — this is the USB/portable hook."""
    override = os.environ.get('MBC2_DATA_DIR')
    if override:
        return Path(override)
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA')
        if base:
            return Path(base) / 'MBC2Dashboard'
    elif sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'MBC2Dashboard'
    return Path.home() / '.mbc2dashboard'

DATA_DIR    = _resolve_data_dir()
DB_PATH     = DATA_DIR / 'mbc2.db'
BACKUP_DIR  = DATA_DIR / 'backups'
LOG_PATH    = DATA_DIR / 'server.log'
BACKUP_KEEP = 14

# ── Logging ────────────────────────────────────────────────────────────────────
# From source: console only.  Frozen exe: console + rotating file in data dir.
def _setup_logging():
    handlers = [logging.StreamHandler(sys.stdout)]
    if getattr(sys, 'frozen', False):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(LOG_PATH, encoding='utf-8'))
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers,
    )

_setup_logging()

# ── DB, motor API, seed file ───────────────────────────────────────────────────
SEED_JSON = RESOURCE_DIR / 'default_programs.json'

sys.path.insert(0, str(RESOURCE_DIR))
import db_manager as db
import motor_api

# Override db_manager's dev-mode defaults with the resolved data-dir paths.
# Must happen before any db.* function is called.
db.DB_PATH     = DB_PATH
db.SCHEMA_PATH = RESOURCE_DIR / 'schema.sql'

# ── Legacy migration ───────────────────────────────────────────────────────────
_migrated_this_run = False

def _migrate_legacy_db():
    """Copy a legacy mbc2.db from beside the app into the new data home.
    COPIES, never moves — the original stays as a fossil backup.
    Only runs when the new data home has no database yet."""
    global _migrated_this_run
    legacy = APP_DIR / 'mbc2.db'
    if DB_PATH.exists() or not legacy.exists():
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy, DB_PATH)
    _migrated_this_run = True
    logging.info(f'[MBC2] Legacy mbc2.db copied to new home: {DB_PATH}')
    try:
        (APP_DIR / 'DATA-HAS-MOVED.txt').write_text(
            'Your MBC2 motor data has moved to a new home:\n'
            f'  {DB_PATH}\n\n'
            f'It was copied there on {time.strftime("%Y-%m-%d")} and this old\n'
            'copy was left in place as a backup. App updates can no longer\n'
            'touch your data. Do not use mbc2.db in THIS folder — it is no\n'
            'longer updated.\n',
            encoding='utf-8',
        )
    except Exception:
        pass  # the note is a courtesy; never block startup over it

# ── Daily rolling backup ───────────────────────────────────────────────────────
def _backup_db():
    """Snapshot the DB once per day using the sqlite3 backup API, which safely
    checkpoints any leftover WAL before writing. Keeps the last 14 daily copies."""
    try:
        if not DB_PATH.exists():
            return
        dest = BACKUP_DIR / f'mbc2-{time.strftime("%Y-%m-%d")}.db'
        if dest.exists():
            return
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        src = sqlite3.connect(str(DB_PATH))
        bak = sqlite3.connect(str(dest))
        try:
            src.backup(bak)
        finally:
            bak.close()
            src.close()
        old = sorted(BACKUP_DIR.glob('mbc2-*.db'))
        for f in old[:-BACKUP_KEEP]:
            f.unlink()
        logging.info(f'[MBC2] Daily backup: {dest.name}')
    except Exception as e:
        logging.warning(f'[MBC2] Daily backup failed: {e}')

# ── Already-running and port-conflict checks ───────────────────────────────────
APP_URL = f'http://127.0.0.1:{PORT}'

def _already_running() -> bool:
    """True if our app is already serving on PORT (responds to /api/ping)."""
    import urllib.request
    try:
        with urllib.request.urlopen(f'{APP_URL}/api/ping', timeout=1) as r:
            return r.status == 200
    except Exception:
        return False

def _port_in_use() -> bool:
    """True if anything at all is listening on PORT."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', PORT)) == 0

def _foreign_port_error():
    """Friendly error when port is taken by a program that isn't our app."""
    msg = (
        f'Port {PORT} is already in use by another program.\n\n'
        'Close the other program and try again,\n'
        'or restart your computer.'
    )
    if os.name == 'nt' and getattr(sys, 'frozen', False):
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, 'MBC2 Dashboard', 0x10)
    else:
        print(f'\n[MBC2] ERROR: {msg}')
    sys.exit(1)

# ── Startup preparation ────────────────────────────────────────────────────────
def _prepare():
    """Run before the server binds: migrate, create data dir, init DB, backup, seed."""
    _migrate_legacy_db()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db.init_db()
    _backup_db()
    try:
        if not db.get_all_profiles() and SEED_JSON.exists():
            count = db.import_programs_from_json(str(SEED_JSON))
            logging.info(f'[MBC2] Seeded {count} break-in profiles from {SEED_JSON.name}')
    except Exception as e:
        logging.warning(f'[MBC2] Seed warning: {e}')

# ── Request handler ────────────────────────────────────────────────────────────
class MBC2Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence per-request logging

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]

        # ── Motor / Profile API ──────────────────────────────────────────────
        if path.startswith('/api/motors') or path.startswith('/api/profiles'):
            motor_api.handle_motor_api(self)
            return

        # ── Keepalive ping ───────────────────────────────────────────────────
        if path == '/api/ping':
            self._json({'ok': True})
            return

        # ── App info: version, data dir, one-time migration notice ───────────
        if path == '/api/info':
            global _migrated_this_run
            self._json({
                'version': APP_VERSION,
                'dataDir': str(DATA_DIR),
                'migrated': _migrated_this_run,
            })
            _migrated_this_run = False  # clear after first read
            return

        # ── Connection tracking ──────────────────────────────────────────────
        if path == '/api/connections/open':
            try:
                connection_id = db.open_connection()
                self._json({'ok': True, 'connection_id': connection_id})
            except Exception as e:
                self._json({'error': str(e)}, 500)
            return

        if path.startswith('/api/connections/') and path.endswith('/sessions'):
            parts = path.split('/')
            if len(parts) == 5:
                try:
                    connection_id = int(parts[3])
                    sessions = db.get_connection_sessions(connection_id)
                    self._json({'sessions': sessions})
                except Exception as e:
                    self._json({'error': str(e)}, 500)
            return

        # ── Crash events ─────────────────────────────────────────────────────
        if path == '/api/crash-events':
            try:
                events = db.get_crash_events()
                self._json({'events': events})
            except Exception as e:
                self._json({'error': str(e)}, 500)
            return

        # ── Sessions list ────────────────────────────────────────────────────
        if path == '/api/sessions':
            try:
                sessions = db.get_all_sessions()
                self._json({'sessions': sessions})
            except Exception as e:
                self._json({'error': str(e)}, 500)
            return

        # ── Session data rows ────────────────────────────────────────────────
        if path.startswith('/api/sessions/') and path.endswith('/data'):
            parts = path.split('/')
            if len(parts) == 5:
                try:
                    session_id = int(parts[3])
                    rows = db.get_session_data(session_id)
                    self._json({'session_id': session_id, 'rows': rows})
                except Exception as e:
                    self._json({'error': str(e)}, 500)
            return

        # ── Session CSV export ───────────────────────────────────────────────
        if path.startswith('/api/sessions/') and path.endswith('/export'):
            parts = path.split('/')
            if len(parts) == 5:
                try:
                    session_id = int(parts[3])
                    csv_text = db.export_session_csv(session_id)
                    if csv_text is None:
                        self._json({'error': 'Session not found'}, 404)
                        return
                    encoded = csv_text.encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/csv')
                    self.send_header('Content-Disposition',
                                     f'attachment; filename="session_{session_id}.csv"')
                    self.send_header('Content-Length', len(encoded))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(encoded)
                except Exception as e:
                    self._json({'error': str(e)}, 500)
            return

        # ── Shutdown ─────────────────────────────────────────────────────────
        if path == '/api/shutdown':
            self._json({'ok': True, 'message': 'Server shutting down'})
            logging.info('[MBC2] Shutdown requested from browser.')
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        # ── Firmware proxy ───────────────────────────────────────────────────
        if path == '/api/firmware/versions':
            try:
                import urllib.request
                req = urllib.request.Request(
                    'http://esp32.miclabo.xyz/versions.csv',
                    headers={'User-Agent': 'MBC2-Dashboard/1.0'}
                )
                with urllib.request.urlopen(req, timeout=3) as r:
                    csv_data = r.read().decode('utf-8')
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/csv')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(csv_data.encode())
                except Exception:
                    pass
            except Exception:
                try:
                    self._json({'error': 'firmware server unavailable'}, 503)
                except Exception:
                    pass
            return

        # ── Serve dashboard HTML ─────────────────────────────────────────────
        if path in ('/', '/index.html', '/mbc2-dashboard.html'):
            html_path = RESOURCE_DIR / 'mbc2-dashboard.html'
            if html_path.exists():
                content = html_path.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
            else:
                self._json({'error': 'Dashboard HTML not found'}, 404)
            return

        self._json({'error': f'Unknown route: {path}'}, 404)

    def do_POST(self):
        path = self.path.split('?')[0]

        # ── Motor / Profile API ──────────────────────────────────────────────
        if path.startswith('/api/motors') or path.startswith('/api/profiles'):
            motor_api.handle_motor_api(self)
            return

        # ── Connection close ─────────────────────────────────────────────────
        if path == '/api/connections/close':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length))
                connection_id = body.get('connection_id')
                end_reason = body.get('end_reason', 'normal')
                if connection_id:
                    db.close_connection(connection_id, end_reason)
                self._json({'ok': True})
            except Exception as e:
                self._json({'error': str(e)}, 500)
            return

        # ── Crash events ─────────────────────────────────────────────────────
        if path == '/api/crash-events':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length))
                event_id = db.log_crash_event(body)
                self._json({'ok': True, 'event_id': event_id})
            except Exception as e:
                self._json({'error': str(e)}, 500)
            return

        # ── Save session to DB ────────────────────────────────────────────────
        if path == '/api/sessions':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length))

                motor_id     = body.get('motor_id')
                session_type = body.get('session_type', 'Breakin')
                rows         = body.get('rows', [])
                notes        = body.get('notes')
                session_id   = body.get('session_id')

                if session_id and not db.session_exists(session_id):
                    session_id = None

                if session_id:
                    if notes:
                        db.update_session_notes(session_id, notes)
                else:
                    if not motor_id:
                        self._json({'error': 'motor_id is required'}, 400)
                        return
                    session_id = db.create_session(
                        motor_id=motor_id,
                        session_type=session_type,
                        notes=notes
                    )

                if rows:
                    db.log_session_data(session_id, rows)

                if body.get('is_baseline'):
                    db.record_benchmark_from_session(
                        session_id=session_id,
                        motor_id=motor_id,
                        benchmark_type=body.get('benchmark_type', 'Periodic'),
                        direction=body.get('direction', 'R'),
                        peak_rpm=body.get('peak_rpm'),
                        avg_rpm=body.get('avg_rpm'),
                        peak_current_ma=body.get('peak_current_ma'),
                        avg_current_ma=body.get('avg_current_ma'),
                        peak_temp_c=body.get('peak_temp'),
                        final_temp_c=body.get('final_temp'),
                        duration_sec=body.get('duration_sec', 120),
                        voltage_v=body.get('voltage_v', 3.0)
                    )

                program_id = body.get('program_id')
                if program_id:
                    db.log_breakin_run(motor_id, [program_id], session_id=session_id)

                self._json({'ok': True, 'session_id': session_id})
            except Exception as e:
                self._json({'error': str(e)}, 500)
            return

        self._json({'error': f'Unknown route: {path}'}, 404)

    def do_DELETE(self):
        path = self.path.split('?')[0]

        # ── Motor / Profile API ──────────────────────────────────────────────
        if path.startswith('/api/motors') or path.startswith('/api/profiles'):
            motor_api.handle_motor_api(self)
            return

        # ── Delete a session and its data ────────────────────────────────────
        if path.startswith('/api/sessions/'):
            parts = path.split('/')
            if len(parts) == 4:
                try:
                    session_id = int(parts[3])
                    db.delete_session(session_id)
                    self._json({'ok': True, 'deleted': session_id})
                except Exception as e:
                    self._json({'error': str(e)}, 500)
            return

        # ── Delete a crash event ─────────────────────────────────────────────
        if path.startswith('/api/crash-events/'):
            parts = path.split('/')
            if len(parts) == 4:
                try:
                    event_id = int(parts[3])
                    db.delete_crash_event(event_id)
                    self._json({'ok': True, 'deleted': event_id})
                except Exception as e:
                    self._json({'error': str(e)}, 500)
            return

        self._json({'error': f'Unknown route: {path}'}, 404)

    def _json(self, data, status=200):
        body = json.dumps(data, default=str).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)


# ── Server class ───────────────────────────────────────────────────────────────
class MBC2Server(socketserver.ThreadingTCPServer):
    # Threaded so slow requests (e.g. the 3s firmware proxy) don't freeze the UI.
    # Safe: db_manager opens a fresh SQLite connection per call (WAL mode).
    allow_reuse_address = True
    daemon_threads = True


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Already running? Open the existing instance and exit.
    if _already_running():
        print('[MBC2] Already running — opening in browser.')
        try:
            webbrowser.open(APP_URL)
        except Exception:
            print(f'[MBC2] Go to {APP_URL} manually.')
        time.sleep(1)
        sys.exit(0)

    # Port blocked by a foreign program?
    if _port_in_use():
        _foreign_port_error()

    _prepare()

    print('=' * 54)
    print(f'  MBC2 Dashboard v{APP_VERSION}')
    print('=' * 54)
    print(f'  Server:  http://localhost:{PORT}')
    print(f'  Data:    {DATA_DIR}')
    print()
    print('  Opens automatically in your browser.')
    print('  Press Ctrl+C to stop manually.')
    print('=' * 54)

    # Bind first, then open the browser — no timer needed.
    with MBC2Server(('127.0.0.1', PORT), MBC2Handler) as httpd:
        try:
            webbrowser.open(APP_URL)
        except Exception:
            print(f'[MBC2] Could not open browser — go to {APP_URL} manually.')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n[MBC2] Server stopped.')
