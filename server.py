#!/usr/bin/env python3
"""
MBC2 Dashboard Server v3.0
- Serves mbc2-dashboard.html
- All data stored in SQLite (mbc2.db) — no CSV session files
- Programs/profiles served from DB only
- CSV export available on demand via /api/sessions/<id>/export
- Auto-opens browser on start
- Shuts down via Stop Server button in app or Ctrl+C
"""

import http.server
import time
import socketserver
import webbrowser
import threading
import json
import os
import sys
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
DASHBOARD_HTML = BASE_DIR / 'mbc2-dashboard.html'

# Seed file for first-run program import
_seed_candidates = [
    BASE_DIR / 'default_programs.json',
    BASE_DIR / 'seed_programs.json',
]
SEED_JSON = next((p for p in _seed_candidates if p.exists()), None)

PORT = 8766

# ── DB setup ─────────────────────────────────────────────────
sys.path.insert(0, str(BASE_DIR))
import db_manager as db
import motor_api

db.init_db()

# Seed programs on first run if profiles table is empty
try:
    if not db.get_all_profiles() and SEED_JSON and SEED_JSON.exists():
        count = db.import_programs_from_json(str(SEED_JSON))
        print(f'[MBC2] Seeded {count} break-in profiles from {SEED_JSON.name}')
except Exception as e:
    print(f'[MBC2] Seed warning: {e}')


# ── Request handler ───────────────────────────────────────────
class MBC2Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence request logging

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]

        # ── Motor / Profile API ───────────────────────────────
        if path.startswith('/api/motors') or path.startswith('/api/profiles'):
            motor_api.handle_motor_api(self)
            return

        # ── Keepalive ping ────────────────────────────────────
        if path == '/api/ping':
            self._json({'ok': True})
            return

        # ── Sessions list (from DB) ───────────────────────────
        if path == '/api/sessions':
            try:
                sessions = db.get_all_sessions()
                self._json({'sessions': sessions})
            except Exception as e:
                self._json({'error': str(e)}, 500)
            return

        # ── Session data rows ─────────────────────────────────
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

        # ── Session CSV export (on demand) ────────────────────
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

        # ── Shutdown ──────────────────────────────────────────
        if path == '/api/shutdown':
            self._json({'ok': True, 'message': 'Server shutting down'})
            print('\n[MBC2] Shutdown requested from browser.')
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        # ── Firmware proxy ────────────────────────────────────
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

        # ── Serve dashboard HTML ──────────────────────────────
        if path in ('/', '/index.html', '/mbc2-dashboard.html'):
            if DASHBOARD_HTML.exists():
                content = DASHBOARD_HTML.read_bytes()
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

        # ── Motor / Profile API ───────────────────────────────
        if path.startswith('/api/motors') or path.startswith('/api/profiles'):
            motor_api.handle_motor_api(self)
            return

        # ── Save session to DB ────────────────────────────────
        # Payload: {
        #   motor_id, session_type, notes,
        #   rows: [ {timestamp_ms, raw_line, mode, program_step,
        #            voltage_mv, current_ma, rpm, temp_c,
        #            elapsed_sec, rpm_cap, kv_efficiency}, ... ],
        #   -- optional benchmark fields --
        #   is_baseline, benchmark_type, direction,
        #   peak_rpm, avg_rpm, peak_current_ma, avg_current_ma,
        #   peak_temp, final_temp, duration_sec, voltage_v,
        #   program_id
        # }
        if path == '/api/sessions':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length))

                motor_id     = body.get('motor_id')
                session_type = body.get('session_type', 'Breakin')
                rows         = body.get('rows', [])
                notes        = body.get('notes')

                if not motor_id:
                    self._json({'error': 'motor_id is required'}, 400)
                    return

                # Create session record
                session_id = db.create_session(
                    motor_id=motor_id,
                    session_type=session_type,
                    notes=notes
                )

                # Store all data rows in session_data table
                if rows:
                    db.log_session_data(session_id, rows)

                # Store benchmark summary if this was a benchmark session
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

                # Log which program was run
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

        # ── Motor / Profile API ───────────────────────────────
        if path.startswith('/api/motors') or path.startswith('/api/profiles'):
            motor_api.handle_motor_api(self)
            return

        # ── Delete a session and its data ─────────────────────
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

        self._json({'error': f'Unknown route: {path}'}, 404)

    def _json(self, data, status=200):
        body = json.dumps(data, default=str).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)


# ── Main ──────────────────────────────────────────────────────
if __name__ == '__main__':
    with socketserver.TCPServer(('', PORT), MBC2Handler) as httpd:
        httpd.allow_reuse_address = True
        url = f'http://localhost:{PORT}'
        print(f'[MBC2] Server running at {url}')
        print(f'[MBC2] Press Ctrl+C to stop manually')
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n[MBC2] Server stopped.')
