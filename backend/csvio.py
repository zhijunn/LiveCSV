# -*- coding: utf-8 -*-
"""CSV reading for LiveCSV.

Key properties:

* **Non-locking reads.**  Files are opened in read-only byte mode and
  closed immediately after the bytes are buffered.  We never hold or write the
  source file, so Office (or any other app) can read/write it concurrently.
  If Office is momentarily mid-write we retry a few times before giving up.

* **Encoding sniffing.**  No external dependency: try a small list of common
  encodings (UTF-8 w/ BOM, UTF-8, GBK, GB18030, Big5, CP1252, Latin-1) and use
  the first that decodes cleanly.  Latin-1 is the unconditional fallback.

* **Correct embedded-newline handling.**  Parsing goes through
  :mod:`csv.reader` over a :class:`io.StringIO`, so quoted fields that span
  multiple lines are preserved.

A small in-memory cache keyed by ``(path, mtime, size, delimiter, encoding)``
avoids re-parsing on every meta-poll and reload when the file has not changed.
"""

import io
import os
import csv
import time
import threading

# Order matters: more specific / likely first.  latin-1 always succeeds.
ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb18030", "big5", "cp1252", "latin-1"]

# Candidate field separators for "auto" detection, in priority order.
_DELIMITERS = [",", ";", "\t", "|"]

# Files larger than this are truncated to the first MAX_READ_BYTES for display
# and filtering (keeps the browser responsive on very large files).
MAX_READ_BYTES = 64 * 1024 * 1024  # 64 MB


def read_bytes(path, attempts=4, delay=0.12, limit=None):
    """Read raw bytes, retrying briefly if another process is mid-write.

    If *limit* is given, only the first *limit* bytes are read.
    """
    last = None
    for _ in range(attempts):
        try:
            with open(path, "rb") as f:
                return f.read(limit) if limit else f.read()
        except (PermissionError, OSError) as e:
            last = e
            time.sleep(delay)
    raise last


def decode_bytes(raw, encoding=None):
    """Return ``(text, encoding)`` for *raw* bytes.

    If *encoding* is given it is honoured; otherwise the encoding list is tried
    in turn.
    """
    if encoding:
        try:
            return raw.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            pass  # fall through to the auto list
    for enc in ENCODINGS:
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", errors="replace"), "latin-1"


def decode_bytes_partial(raw, encoding=None):
    """Decode a possibly-truncated byte stream.

    The encoding is detected from the first 64 KB using strict decode (so a
    wrong codec is not silently accepted), then the full *raw* is decoded with
    that encoding using ``errors="ignore"`` so an incomplete multi-byte
    character at the tail does not raise.
    """
    sample = raw[:65536]
    detected = None
    if encoding:
        try:
            sample.decode(encoding)
            detected = encoding
        except (UnicodeDecodeError, LookupError):
            pass
    if not detected:
        for enc in ENCODINGS:
            try:
                sample.decode(enc)
                detected = enc
                break
            except (UnicodeDecodeError, LookupError):
                continue
    if not detected:
        detected = "latin-1"
    return raw.decode(detected, errors="ignore"), detected


def read_text(path, encoding=None):
    raw = read_bytes(path)
    return decode_bytes(raw, encoding)


def parse_csv(text, delimiter=","):
    """Parse decoded *text* into a list of rows (each a list of str)."""
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return list(reader)


def sniff_delimiter(text):
    """Pick the delimiter that occurs most often on the first non-empty line."""
    first = ""
    for line in text.splitlines():
        if line.strip():
            first = line
            break
    best, best_n = ",", -1
    for d in _DELIMITERS:
        n = first.count(d)
        if n > best_n:
            best, best_n = d, n
    return best


_CACHE = {}
_CACHE_LOCK = threading.Lock()


def get_parsed(path, delimiter=",", encoding=None):
    """Return a parsed payload for *path*, using the cache when possible.

    The result dict contains: ``columns``, ``rows`` (excluding the header row),
    ``encoding``, ``delimiter``, ``rowCount``, ``mtime``, ``size``,
    ``truncated`` (bool), ``totalSize`` (bytes, only when truncated).
    """
    st = os.stat(path)
    key = (path, st.st_mtime_ns, st.st_size, delimiter, encoding)
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
    if hit is not None:
        return hit

    total_size = st.st_size
    truncated = total_size > MAX_READ_BYTES
    if truncated:
        raw = read_bytes(path, limit=MAX_READ_BYTES)
        text, detected_enc = decode_bytes_partial(raw, encoding)
        # Cut at the last newline so every retained row is complete (a partial
        # tail row could have the wrong number of columns).
        last_nl = text.rfind("\n")
        if last_nl > 0:
            text = text[:last_nl]
    else:
        raw = read_bytes(path)
        text, detected_enc = decode_bytes(raw, encoding)

    if delimiter == "auto":
        delimiter = sniff_delimiter(text)

    rows = parse_csv(text, delimiter=delimiter)

    if not rows:
        columns, data = [], []
    else:
        columns = rows[0]
        data = rows[1:]

    payload = {
        "columns": columns,
        "rows": data,
        "encoding": detected_enc,
        "delimiter": delimiter,
        "rowCount": len(data),
        "mtime": st.st_mtime_ns,
        "size": st.st_size,
        "truncated": truncated,
    }
    if truncated:
        payload["totalSize"] = total_size

    with _CACHE_LOCK:
        if len(_CACHE) > 16:
            _CACHE.clear()
        _CACHE[key] = payload
    return payload


def stat_meta(path):
    """Lightweight metadata for change polling: ``(exists, mtime_ns, size)``."""
    if not os.path.exists(path):
        return False, None, None
    st = os.stat(path)
    return True, st.st_mtime_ns, st.st_size
