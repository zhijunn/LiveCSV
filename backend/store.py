# -*- coding: utf-8 -*-
"""Persistent state for LiveCSV.

All durable state lives in ``state.json`` next to the application:

* ``history`` – recently opened files (most-recent first), shared across all
  windows.  Per-file view state (filters, column widths, pinned columns, …)
  is kept client-side in ``localStorage`` and is *not* stored here.

Writes are serialised by a process-local lock and written atomically
(temp file + ``os.replace``) so a crash mid-write cannot corrupt the store.
"""

import os
import json
import time
import threading

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(APP_DIR, "state.json")

HISTORY_LIMIT = 20

# Serialises all reads-modify-writes performed in this process.
_LOCK = threading.Lock()


def _default_state():
    return {"history": []}


def load_state():
    """Load and normalise the persisted state (never raises)."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return _default_state()
    if not isinstance(data, dict):
        return _default_state()
    data.setdefault("history", [])
    # Drop legacy keys from older versions (lastOpened, windows) so the file
    # shrinks on the next save.
    data.pop("lastOpened", None)
    data.pop("windows", None)
    return data


def save_state(state):
    """Atomically write the full state."""
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def lock():
    """Acquire the store lock (use as a context manager via ``with store.lock():``)."""
    return _LOCK


def record_open(state, path, name=None, source="local"):
    """Promote ``path`` to the front of the history.

    ``name``   – display name (defaults to the basename of *path*); for uploaded
                 copies this is the user's original filename rather than the
                 internal managed filename.
    ``source`` – ``"local"`` (a real file picked via the system dialog) or
                 ``"upload"`` (a browser-uploaded copy managed by the app).
    """
    name = name or os.path.basename(path)
    entry = {"path": path, "name": name, "source": source, "openedAt": int(time.time())}
    hist = [h for h in state["history"] if h.get("path") != path]
    hist.insert(0, entry)
    state["history"] = hist[:HISTORY_LIMIT]


def clear_history(state):
    """Remove all entries from history."""
    state["history"] = []


def remove_history(state, path):
    """Remove a single *path* from history."""
    state["history"] = [h for h in state["history"] if h.get("path") != path]
