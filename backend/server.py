# -*- coding: utf-8 -*-
"""LiveCSV — Flask application and HTTP API.

Defines the WSGI app and all routes (the page plus ``/api/*``).  It is started
by :mod:`livecsv`, the command-line launcher.  Heavy lifting lives in sibling
modules:

* :mod:`store`     – persistent state (recently-opened history).
* :mod:`csvio`     – non-locking CSV reading, encoding sniffing, caching.
* :mod:`nativeops` – native file dialog, open-with-default, reveal-in-folder.

The frontend (``frontend/index.html`` + split CSS/JS) is a Vue 3 app served
at ``/``; Vue itself is bundled locally under ``static/`` so the app runs
fully offline.
"""

import os
import uuid
import logging
import threading

from flask import Flask, request, jsonify, send_file, send_from_directory

from . import store
from . import csvio
from . import nativeops

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_FILE = os.path.join(APP_DIR, "frontend", "index.html")
FRONTEND_DIR = os.path.join(APP_DIR, "frontend")
SAMPLE_DIR = os.path.join(APP_DIR, "samples")
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")   # browser-uploaded copies live here
LOG_DIR = os.path.join(APP_DIR, "logs")         # server run logs (archived monthly)
ALLOWED_EXTS = {".csv", ".tsv", ".txt"}        # accepted file extensions


def _check_ext(path):
    """Return an error response tuple if *path* has an unsupported extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in ALLOWED_EXTS:
        return jsonify({"ok": False, "error": "unsupported file type: %s (allowed: .csv .tsv .txt)" % ext}), 400
    return None

app = Flask(__name__, root_path=APP_DIR)
log = logging.getLogger("livecsv")


# ===========================================================================
# Page
# ===========================================================================
@app.route("/")
def index():
    return send_file(INDEX_FILE)


@app.route("/frontend/<path:filename>")
def frontend(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.after_request
def _no_cache_index(resp):
    # The frontend is under active iteration; always serve the latest
    # index.html and our split assets so a stale browser cache can't run old
    # (buggy) code after a refresh. Third-party assets (Vue) are left cacheable.
    if request.path == "/" or request.path.startswith("/frontend/"):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


# ===========================================================================
# API — file selection & history
# ===========================================================================
@app.route("/api/history")
def api_history():
    with store.lock():
        return jsonify({"history": store.load_state().get("history", [])})


@app.route("/api/history/clear", methods=["POST"])
def api_history_clear():
    with store.lock():
        state = store.load_state()
        store.clear_history(state)
        store.save_state(state)
    log.info("history cleared")
    return jsonify({"ok": True})


@app.route("/api/history/remove", methods=["POST"])
def api_history_remove():
    data = request.get_json(force=True) or {}
    path = data.get("path")
    if not path:
        return jsonify({"ok": False, "error": "no path"}), 400
    with store.lock():
        state = store.load_state()
        store.remove_history(state, path)
        store.save_state(state)
    log.info("removed from history: %s", path)
    return jsonify({"ok": True})


@app.route("/api/samples")
def api_samples():
    """Bundled sample files (lets the UI offer a demo with no file chosen)."""
    out = []
    if os.path.isdir(SAMPLE_DIR):
        for fn in sorted(os.listdir(SAMPLE_DIR)):
            if fn.lower().endswith((".csv", ".tsv", ".txt")):
                out.append(os.path.join(SAMPLE_DIR, fn))
    return jsonify({"samples": out})


@app.route("/api/pick", methods=["POST"])
def api_pick():
    """Open the native file dialog. Returns ``{path, name}`` or ``{path: null}``."""
    path = nativeops.pick_file()
    if path:
        return jsonify({"path": path, "name": os.path.basename(path)})
    return jsonify({"path": None})


# ===========================================================================
# API — opening / reading a file
# ===========================================================================
@app.route("/api/open", methods=["POST"])
def api_open():
    """Register a file as opened (pushes it to the front of history).

    Body: ``{path, name?, source?}``.  Does not return row data; the client
    then calls :http:get:`/api/data` (possibly with a remembered delimiter).
    """
    data = request.get_json(force=True) or {}
    path = data.get("path")
    display_name = data.get("name")          # optional friendly name (uploads)
    source = data.get("source") or "local"   # "local" | "upload"
    if not path:
        return jsonify({"ok": False, "error": "no path"}), 400
    path = os.path.normpath(path)
    ext_err = _check_ext(path)
    if ext_err:
        with store.lock():
            state = store.load_state()
            store.remove_history(state, path)
            store.save_state(state)
        return ext_err
    if not os.path.isfile(path):
        return jsonify({"ok": False, "error": "file not found"}), 404

    try:
        _, mtime, size = csvio.stat_meta(path)
    except OSError as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    with store.lock():
        state = store.load_state()
        store.record_open(state, path, name=display_name, source=source)
        store.save_state(state)
    log.info("opened [%s] %s", source, path)

    return jsonify({
        "ok": True,
        "path": path,
        "name": display_name or os.path.basename(path),
        "source": source,
        "mtime": mtime,
        "size": size,
    })


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Receive a file chosen via the browser's ``<input type="file">``.

    Browsers cannot expose the real filesystem path of a chosen file, so the
    content is uploaded and stored as a managed copy under ``uploads/``.  The
    returned path is then used exactly like any local file.  Because it is a
    snapshot, live-update/open-original operate on this copy (the original is
    not watched); use the system dialog for those real-file features.
    """
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "no file part"}), 400
    f = request.files["file"]
    original = f.filename or "uploaded.csv"
    # keep only the basename and a short unique suffix to avoid collisions
    base = os.path.basename(original) or "uploaded"
    name, ext = os.path.splitext(base)
    ext_err = _check_ext(base)
    if ext_err: return ext_err
    safe_name = "%s__%s%s" % (name, uuid.uuid4().hex[:8], ext or ".csv")
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        dest = os.path.join(UPLOAD_DIR, safe_name)
        f.save(dest)
    except OSError as e:
        return jsonify({"ok": False, "error": "save failed: %s" % e}), 500
    log.info("uploaded %s -> %s", base, dest)
    return jsonify({"ok": True, "path": dest, "name": base, "source": "upload"})


@app.route("/api/data")
def api_data():
    """Return parsed rows for a file (cached by path+mtime+delim+encoding)."""
    path = request.args.get("path")
    delimiter = request.args.get("delim") or ","
    encoding = request.args.get("encoding") or None
    if not path:
        return jsonify({"error": "no path"}), 400
    path = os.path.normpath(path)
    if not os.path.isfile(path):
        return jsonify({"error": "file not found"}), 404
    try:
        payload = csvio.get_parsed(path, delimiter=delimiter, encoding=encoding)
    except Exception as e:  # noqa: BLE001 - surface any read error to the client
        return jsonify({"error": "read failed: %s" % e}), 500
    return jsonify(payload)


@app.route("/api/meta")
def api_meta():
    """Cheap change-detection probe used by the client's polling loop."""
    path = request.args.get("path")
    if not path:
        return jsonify({"error": "no path"}), 400
    path = os.path.normpath(path)
    exists, mtime, size = csvio.stat_meta(path)
    if not exists:
        return jsonify({"exists": False})
    return jsonify({"exists": True, "mtime": mtime, "size": size})


# ===========================================================================
# API — shell conveniences & lifecycle
# ===========================================================================
@app.route("/api/open-native", methods=["POST"])
def api_open_native():
    data = request.get_json(force=True) or {}
    path = data.get("path")
    if not path or not os.path.exists(path):
        return jsonify({"ok": False, "error": "invalid path"}), 400
    return jsonify({"ok": nativeops.open_default(path)})


@app.route("/api/reveal", methods=["POST"])
def api_reveal():
    data = request.get_json(force=True) or {}
    path = data.get("path")
    if not path or not os.path.exists(path):
        return jsonify({"ok": False, "error": "invalid path"}), 400
    return jsonify({"ok": nativeops.reveal(path)})


@app.route("/api/quit", methods=["POST"])
def api_quit():
    """Stop the server (used by a launcher/tray, not the normal UI flow)."""
    threading.Timer(0.2, lambda: os._exit(0)).start()
    return jsonify({"ok": True})


# ===========================================================================
# Upload maintenance
# ===========================================================================
def prune_uploads(limit=100):
    """Bound growth of the uploads dir: keep only the *limit* newest copies."""
    try:
        if not os.path.isdir(UPLOAD_DIR):
            return
        files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR)]
        files = [f for f in files if os.path.isfile(f)]
        if len(files) <= limit:
            return
        files.sort(key=lambda p: os.path.getmtime(p))
        for p in files[:len(files) - limit]:
            try:
                os.remove(p)
            except OSError:
                pass
    except OSError:
        pass
