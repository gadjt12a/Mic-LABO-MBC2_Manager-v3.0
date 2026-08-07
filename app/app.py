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

try:
    import pyi_splash as _splash
except ImportError:
    _splash = None


def _dismiss_splash():
    if _splash:
        try:
            _splash.close()
        except Exception:
            pass


_window = None


def _on_window_closing():
    """Ask before discarding an in-progress recording.

    The page's own beforeunload warning does nothing under WebView2 — closing
    the window mid-recording silently threw away every unsaved row. Only asks
    when there is something to lose: an armed recording with no rows yet is not
    worth a dialog.

    Returning False cancels the close. Anything unexpected here must let the
    window close, or a bug in this handler would trap the user in the app.
    """
    try:
        state = srv.get_recording_state()
        if not state.get('active') or state.get('rows', 0) < 1:
            return True
        rows = state['rows']
        return bool(_window.create_confirmation_dialog(
            'Recording in progress',
            f'{rows} recorded row{"s" if rows != 1 else ""} have not been saved '
            f'to the database yet.\n\nClose anyway and lose them?'))
    except Exception as exc:
        print(f'[MBC2] close confirmation failed ({exc}); closing anyway')
        return True


def _on_window_closed():
    """Close the open connection record, then exit.

    os._exit(0) on its own kills this process — server included — before the
    page's pagehide beacon can be served, so the connections row stayed open
    forever. The server runs in this same process, so it can close the row
    directly here; nothing has to survive the shutdown.
    """
    try:
        srv.close_open_connection('window_closed')
    except Exception:
        pass    # never block the exit on bookkeeping
    os._exit(0)


def _enable_dpi_awareness():
    """Tell Windows we handle scaling ourselves.

    Without this the process is DPI-unaware: Windows sizes the window in
    physical pixels while WebView2 lays the page out in CSS pixels and then
    scales it by the display factor. On a 125% display a 1400 px window gets
    ~1750 px of content and the right edge (Clear, Stop Server) is cut off
    with no reflow. Must run before the window is created.
    """
    if sys.platform != 'win32':
        return
    import ctypes
    try:
        # Per-monitor v2 — Windows 10 1703+. Correct across mixed-DPI monitors.
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system DPI aware
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # Vista+ fallback
    except Exception:
        pass


def _window_size(preferred=(1400, 900)):
    """Clamp the window to the usable desktop, in the units pywebview wants.

    create_window takes logical (DPI-scaled) pixels, but webview.screens
    reports physical ones — on a 125% display that is 1920x1200 vs the 1536x960
    the window sizes are measured in. Mixing the two silently disables the
    clamp, so derive everything from the work area and divide by the scale.
    Work area excludes the taskbar; the margins leave room for the title bar.
    """
    w, h = preferred
    if sys.platform != 'win32':
        return w, h
    import ctypes

    # RECT is declared here rather than taken from ctypes.wintypes: PyInstaller
    # does not bundle wintypes for this app, so importing it works from source
    # and raises ImportError in the frozen exe - which is exactly how this
    # clamp silently did nothing on the first attempt.
    class RECT(ctypes.Structure):
        _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                    ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

    try:
        scale = ctypes.windll.user32.GetDpiForSystem() / 96.0 or 1.0
        rect = RECT()
        # SPI_GETWORKAREA = 0x0030
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        work_w = int((rect.right - rect.left) / scale)
        work_h = int((rect.bottom - rect.top) / scale)
        if work_w > 0 and work_h > 0:
            w = min(w, work_w - 40)
            h = min(h, work_h - 60)
    except Exception as exc:
        # Never fatal - fall back to the preferred size - but say so, so a
        # failure here cannot hide again.
        print(f'[MBC2] window size clamp failed ({exc}); using {w}x{h}')
    return max(w, 900), max(h, 600)


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
    _enable_dpi_awareness()
    win_w, win_h = _window_size()

    # If another MBC2 instance is already running, just open a window onto it.
    if srv._already_running():
        window = webview.create_window(
            f'MBC2 Dashboard v{srv.APP_VERSION}',
            f'http://127.0.0.1:{srv.PORT}',
            width=win_w, height=win_h, min_size=(900, 600),
        )
        window.events.loaded += _dismiss_splash
        window.events.closed += lambda: os._exit(0)
        webview.start()
        return

    # Port taken by something else entirely.
    if srv._port_in_use():
        # Dismiss the splash first: it is normally closed by the window's
        # 'loaded' event, which never fires on the error paths, so it would sit
        # on screen beside the message box until the user clicked OK.
        _dismiss_splash()
        srv._foreign_port_error()
        return

    t = threading.Thread(target=_start_server, daemon=True)
    t.start()

    if not _wait_for_server():
        _dismiss_splash()
        srv._foreign_port_error()
        return

    window = webview.create_window(
        f'MBC2 Dashboard v{srv.APP_VERSION}',
        f'http://127.0.0.1:{srv.PORT}',
        width=win_w, height=win_h, min_size=(900, 600),
    )
    global _window
    _window = window
    window.events.loaded += _dismiss_splash
    window.events.closing += _on_window_closing
    window.events.closed += _on_window_closed
    webview.start()


if __name__ == '__main__':
    main()
