# -*- coding: utf-8 -*-
"""LiveCSV — launcher / command-line entry point.

Parses CLI arguments, picks a free localhost port, configures logging, opens a
browser (and the Windows tray), then runs the Flask app defined in
:mod:`server`.  All HTTP/page/API logic lives there; this module only boots it.

Run::

    python livecsv.py            # auto-picks a free localhost port, opens a browser
    python livecsv.py --port 8080 --no-browser
    python livecsv.py --log-level INFO
"""

import os
import socket
import logging
import threading
import argparse

from backend.server import app, prune_uploads, LOG_DIR
from backend.log import setup_logging


def find_free_port(preferred=53170):
    for p in range(preferred, preferred + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    import webbrowser

    ap = argparse.ArgumentParser(description="LiveCSV (local browser app)")
    ap.add_argument("--port", type=int, default=None, help="port (default: auto)")
    ap.add_argument("--no-browser", action="store_true",
                    help="do not open a browser automatically")
    ap.add_argument("--log-level", default="WARNING",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    help="logging level (default: WARNING; use INFO for verbose)")
    args = ap.parse_args()

    port = args.port or find_free_port()
    prune_uploads()
    log_level = getattr(logging, args.log_level, logging.WARNING)
    log_file = setup_logging(LOG_DIR, level=log_level)
    url = "http://127.0.0.1:%d/" % port
    log = logging.getLogger("livecsv")
    log.info("LiveCSV starting at %s | port=%d | pid=%d", url, port, os.getpid())
    log.info("logging to %s", log_file)
    print("LiveCSV running at %s" % url)

    # Windows tray icon: Open WebUI / Quit. Best-effort.
    try:
        from backend import tray
        tray.start(url, on_quit=lambda: os._exit(0))
        log.info("tray icon started")
    except Exception as e:  # pragma: no cover
        log.warning("tray icon unavailable: %s", e)

    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url, new=2)).start()

    # threaded=True so a blocking native file dialog cannot stall other requests.
    app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
