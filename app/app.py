#!/usr/bin/env python3
"""
MBC2 Dashboard — pywebview entry point.

Starts the HTTP server in a background thread, waits for it to bind, then
opens a native pywebview window pointing at http://127.0.0.1:8766.

When the user closes the window (or clicks Stop Server, which calls os._exit),
the process exits cleanly.
"""

import os
import sys
import threading
import time

# ── PyInstaller: add unpacked bundle to path ───────────────────────────────────
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)

import server as srv
import webview


def _start_server():
    srv._prepare()
    with srv.MBC2Server(('127.0.0.1', srv.PORT), srv.MBC2Handler) as httpd:
        httpd.serve_forever()


def _wait_for_server(timeout: float = 15.0) -> bool:
    import urllib.request
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f'http://127.0.0.1:{srv.PORT}/api/ping', timeout=0.5
            ):
                return True
        except Exception:
            time.sleep(0.1)
    return False


def main():
    # If another MBC2 instance is already running, just open a window onto it.
    if srv._already_running():
        window = webview.create_window(
            f'MBC2 Dashboard v{srv.APP_VERSION}',
            f'http://127.0.0.1:{srv.PORT}',
            width=1400, height=900, min_size=(900, 600),
        )
        window.events.closed += lambda: os._exit(0)
        webview.start()
        return

    # Port taken by something else entirely.
    if srv._port_in_use():
        srv._foreign_port_error()
        return

    t = threading.Thread(target=_start_server, daemon=True)
    t.start()

    if not _wait_for_server():
        srv._foreign_port_error()
        return

    window = webview.create_window(
        f'MBC2 Dashboard v{srv.APP_VERSION}',
        f'http://127.0.0.1:{srv.PORT}',
        width=1400, height=900, min_size=(900, 600),
    )
    window.events.closed += lambda: os._exit(0)
    webview.start()


if __name__ == '__main__':
    main()
