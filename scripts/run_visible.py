"""run_visible.py - launch browser_cli CLI commands with forced-visible windows.

Background
----------
Some launching environments (automation agents, sandboxes, CI shells) spawn
child processes with SW_HIDE in STARTUPINFO.wShowWindow. pywebview / WinForms
windows are therefore created on the interactive desktop (WinSta0\\Default)
but stay invisible: IsWindowVisible() returns False even though .NET reports
Visible=True. The WebView renders fine and all APIs work - only the window is
not visible on the user's screen.

This wrapper polls for the process's own top-level windows and calls
ShowWindow(SW_SHOW) so the browser windows actually appear. It is safe for
headless runs too (no windows to show -> no-op).

Usage
-----
    python scripts/run_visible.py <browser_cli args...>

Examples
--------
    python scripts/run_visible.py webui --port 8125 --max-windows 1 --no-open
    python scripts/run_visible.py fill-steps --url https://www.baidu.com \
        --step "wait:#kw:30" --step "fill:#kw:rest" --step "sleep:30"

See browser_cli/TROUBLESHOOTING.md section 1.1 for the full story.
"""
import ctypes
import os
import sys
import threading
import time

_u = ctypes.windll.user32
CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


@CB
def _enum_cb(hwnd, lparam):
    pid = ctypes.c_uint32()
    _u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        if not _u.IsWindowVisible(hwnd):
            _u.ShowWindow(hwnd, 5)  # SW_SHOW
    return True


def _force_show_loop(stop):
    while not stop.is_set():
        try:
            _u.EnumWindows(_enum_cb, 0)
        except Exception:
            pass
        stop.wait(0.3)


def main():
    # Project root = parent of this file's parent (scripts/..)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    from browser_cli.cli import main as cli_main

    stop = threading.Event()
    t = threading.Thread(target=_force_show_loop, args=(stop,), daemon=True)
    t.start()
    try:
        cli_main(sys.argv[1:])
    finally:
        stop.set()


if __name__ == "__main__":
    main()
