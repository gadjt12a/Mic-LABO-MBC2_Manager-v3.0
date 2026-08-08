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
import queue
import shutil
import socketserver
import sqlite3
import sys
import threading
import time
import webbrowser
from pathlib import Path

try:
    import serial
    import serial.tools.list_ports as _list_ports
    _PYSERIAL = True
except ImportError:
    _PYSERIAL = False

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

# ── Connection-record lifecycle ────────────────────────────────────────────────
# The frontend opens a connections row and is supposed to close it from its
# pagehide handler with a sendBeacon. In the packaged app that never works:
# closing the window calls os._exit(0), which kills this process — and the HTTP
# server with it — before the beacon can be served. Verified 2026-08-07: not one
# connection in the database had ever been closed with 'tab_closed'.
#
# So the server keeps its own note of the open row and closes it on the way out.
# That does not depend on the page getting a chance to say anything.
_open_connection_id = None
_open_connection_lock = threading.Lock()


def _track_open_connection(connection_id):
    global _open_connection_id
    with _open_connection_lock:
        _open_connection_id = connection_id


def _forget_open_connection(connection_id=None):
    global _open_connection_id
    with _open_connection_lock:
        if connection_id is None or _open_connection_id == connection_id:
            _open_connection_id = None


def close_open_connection(reason: str = 'app_closed'):
    """Close the connection row this run opened, if it is still open."""
    global _open_connection_id
    with _open_connection_lock:
        cid = _open_connection_id
        _open_connection_id = None
    if cid is None:
        return
    try:
        db.close_connection(cid, reason)
        logging.info(f'[MBC2] Closed connection {cid} ({reason})')
    except Exception as e:
        logging.warning(f'[MBC2] Could not close connection {cid}: {e}')


# What the page is currently recording, so the window-close handler can ask
# before throwing away rows that were never saved. Reported by the frontend;
# the server never infers it.
_recording_state = {'active': False, 'rows': 0}


def set_recording_state(active: bool, rows: int = 0):
    with _open_connection_lock:
        _recording_state['active'] = bool(active)
        _recording_state['rows'] = int(rows or 0)


def get_recording_state() -> dict:
    with _open_connection_lock:
        return dict(_recording_state)


def _close_dangling_connections():
    """Close rows left open by a previous run that died without saying so.

    Their ended_at is unknown, so it is recorded as the last moment we can
    evidence rather than guessed: nothing here invents a duration.
    """
    try:
        with db.get_connection() as conn:
            db._ensure_connections_table(conn)
            cur = conn.execute("""
                UPDATE connections
                SET ended_at = COALESCE(ended_at, started_at),
                    end_reason = 'unknown'
                WHERE ended_at IS NULL
            """)
            conn.commit()
            if cur.rowcount:
                logging.info(f'[MBC2] Closed {cur.rowcount} dangling connection '
                             f'record(s) from previous runs')
    except Exception as e:
        logging.warning(f'[MBC2] Dangling connection cleanup failed: {e}')


# ── Already-running and port-conflict checks ───────────────────────────────────
APP_URL = f'http://127.0.0.1:{PORT}'

# How long to wait for a loopback connection before calling the port free.
#
# This machine does not refuse connections to a closed loopback port promptly:
# a blocking connect_ex takes ~2.0s to return WSAECONNREFUSED, and the urllib
# probe simply burned its whole timeout. Between them they spent ~3s of every
# launch proving nothing was listening, against ~0.04s of actual startup work.
#
# A process that really is listening accepts on loopback immediately — the TCP
# handshake completes in the kernel regardless of how busy the app is — so
# anything slower than this is not a running instance.
PROBE_TIMEOUT = 0.35

def _port_in_use() -> bool:
    """True if anything at all is listening on PORT."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(PROBE_TIMEOUT)
        try:
            return s.connect_ex(('127.0.0.1', PORT)) == 0
        except OSError:
            return False

def _ping_ok() -> bool:
    """True if whatever is on PORT answers our /api/ping."""
    import urllib.request
    try:
        with urllib.request.urlopen(f'{APP_URL}/api/ping', timeout=1) as r:
            return r.status == 200
    except Exception:
        return False

def _probe_port() -> str:
    """One probe, three answers: 'free', 'ours', or 'foreign'.

    Callers used to ask _already_running() and then _port_in_use(), paying the
    full cost of both on the common path where the port is simply free.
    """
    if not _port_in_use():
        return 'free'
    return 'ours' if _ping_ok() else 'foreign'

def _already_running() -> bool:
    """True if our app is already serving on PORT (responds to /api/ping)."""
    return _probe_port() == 'ours'

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
    _close_dangling_connections()
    _backup_db()
    try:
        if not db.get_all_profiles() and SEED_JSON.exists():
            count = db.import_programs_from_json(str(SEED_JSON))
            logging.info(f'[MBC2] Seeded {count} break-in profiles from {SEED_JSON.name}')
    except Exception as e:
        logging.warning(f'[MBC2] Seed warning: {e}')

# ── Serial manager ─────────────────────────────────────────────────────────────
class SerialManager:
    """Owns the serial port and broadcasts incoming lines to SSE subscribers."""

    def __init__(self):
        self._port   = None
        self._lock   = threading.Lock()
        self._subs   = []   # list of queue.Queue, one per SSE client
        self._thread = None

    def list_ports(self):
        if not _PYSERIAL:
            return []
        return [
            {'device': p.device, 'description': p.description or p.device}
            for p in _list_ports.comports()
        ]

    def connect(self, port_name: str) -> dict:
        if not _PYSERIAL:
            return {'ok': False, 'error': 'pyserial not installed'}
        with self._lock:
            if self._port and self._port.is_open:
                try:
                    self._port.close()
                except Exception:
                    pass
            try:
                self._port = serial.Serial(port_name, 115200, timeout=0.1)
            except Exception as e:
                self._port = None
                return {'ok': False, 'error': str(e)}
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        return {'ok': True, 'port': port_name}

    def disconnect(self):
        with self._lock:
            if self._port:
                try:
                    self._port.close()
                except Exception:
                    pass
                self._port = None

    def send(self, cmd: str) -> bool:
        with self._lock:
            if not self._port or not self._port.is_open:
                return False
            try:
                self._port.write((cmd + '\n').encode('utf-8'))
                return True
            except Exception:
                return False

    def subscribe(self) -> queue.Queue:
        q = queue.Queue(maxsize=500)
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            try:
                self._subs.remove(q)
            except ValueError:
                pass

    def _broadcast(self, msg: str):
        with self._lock:
            dead = []
            for q in self._subs:
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._subs.remove(q)

    def _read_loop(self):
        buf = b''
        while True:
            with self._lock:
                if not self._port or not self._port.is_open:
                    break
                p = self._port
            try:
                chunk = p.read(p.in_waiting or 1)
                if chunk:
                    buf += chunk
                    while b'\n' in buf:
                        line, buf = buf.split(b'\n', 1)
                        text = line.decode('utf-8', errors='replace').rstrip('\r')
                        if text:
                            self._broadcast(f'data: {text}\n\n')
            except Exception:
                break
        self._broadcast('event: disconnect\ndata: \n\n')


_serial = SerialManager()


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

        # ── Motor / Profile / AccelTest API ──────────────────────────────────
        if (path.startswith('/api/motors') or path.startswith('/api/profiles')
                or path.startswith('/api/accel')):
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
                _track_open_connection(connection_id)
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

        # ── Serial: list available COM ports ─────────────────────────────────
        if path == '/api/ports':
            self._json({'ports': _serial.list_ports()})
            return

        # ── Serial: SSE stream of incoming lines ──────────────────────────────
        if path == '/api/serial/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            q = _serial.subscribe()
            try:
                while True:
                    try:
                        msg = q.get(timeout=15)
                        self.wfile.write(msg.encode('utf-8'))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b': keep-alive\n\n')
                        self.wfile.flush()
            except Exception:
                pass
            finally:
                _serial.unsubscribe(q)
            return

        # ── Shutdown ─────────────────────────────────────────────────────────
        if path == '/api/shutdown':
            self._json({'ok': True, 'message': 'Server shutting down'})
            logging.info('[MBC2] Shutdown requested.')
            close_open_connection('app_closed')
            def _do_exit():
                time.sleep(0.2)
                os._exit(0)
            threading.Thread(target=_do_exit, daemon=True).start()
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

        # ── Motor / Profile / AccelTest API ──────────────────────────────────
        if (path.startswith('/api/motors') or path.startswith('/api/profiles')
                or path.startswith('/api/accel')):
            motor_api.handle_motor_api(self)
            return

        # ── Serial: connect to a COM port ────────────────────────────────────
        if path == '/api/serial/connect':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body   = json.loads(self.rfile.read(length))
                result = _serial.connect(body.get('port', ''))
                self._json(result)
            except Exception as e:
                self._json({'ok': False, 'error': str(e)}, 500)
            return

        # ── Serial: disconnect ────────────────────────────────────────────────
        if path == '/api/serial/disconnect':
            _serial.disconnect()
            self._json({'ok': True})
            return

        # ── Serial: send command to device ────────────────────────────────────
        if path == '/api/serial/send':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body   = json.loads(self.rfile.read(length))
                ok     = _serial.send(body.get('cmd', ''))
                self._json({'ok': ok})
            except Exception as e:
                self._json({'ok': False, 'error': str(e)}, 500)
            return

        # ── Connection close ─────────────────────────────────────────────────
        if path == '/api/recording/state':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                set_recording_state(body.get('active'), body.get('rows'))
                self._json({'ok': True})
            except Exception as e:
                self._json({'error': str(e)}, 500)
            return

        if path == '/api/connections/close':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length))
                connection_id = body.get('connection_id')
                end_reason = body.get('end_reason', 'normal')
                if connection_id:
                    db.close_connection(connection_id, end_reason)
                    _forget_open_connection(connection_id)
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

        # ── Motor / Profile / AccelTest API ──────────────────────────────────
        if (path.startswith('/api/motors') or path.startswith('/api/profiles')
                or path.startswith('/api/accel')):
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
    # One probe covers both questions below.
    port_state = _probe_port()

    # Already running? Open the existing instance and exit.
    if port_state == 'ours':
        print('[MBC2] Already running — opening in browser.')
        try:
            webbrowser.open(APP_URL)
        except Exception:
            print(f'[MBC2] Go to {APP_URL} manually.')
        time.sleep(1)
        sys.exit(0)

    # Port blocked by a foreign program?
    if port_state == 'foreign':
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
