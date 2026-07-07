# -*- coding: utf-8 -*-
"""Server-side logging (logs directory, archived by month).

``setup_logging(log_dir)`` configures the root logger to write to
``<log_dir>/livecsv-YYYY-MM.log`` (one file per calendar month — that file
*is* the monthly archive) and to the console. A long-running process rolls over
to a new month-stamped file automatically at the month boundary.

The Flask/Werkzeug request logger is left at INFO so request lines are captured
too.
"""

import os
import time
import logging


class MonthlyFileHandler(logging.FileHandler):
    """A FileHandler that writes to ``<dir>/<prefix>YYYY-MM.log``.

    When the local calendar month changes (mid-run), it closes the current
    file and opens the next month's file, so logs are always archived by month.
    """

    def __init__(self, directory, prefix="livecsv-"):
        self._directory = directory
        self._prefix = prefix
        os.makedirs(directory, exist_ok=True)
        self._month = self._month_key()
        super().__init__(self._path(), encoding="utf-8")

    @staticmethod
    def _month_key():
        return time.strftime("%Y-%m")

    def _path(self):
        return os.path.join(self._directory, self._prefix + self._month_key() + ".log")

    def emit(self, record):
        m = self._month_key()
        if m != self._month:                       # month rolled over -> switch files
            self._month = m
            self.close()
            self.baseFilename = self._path()
            self.stream = self._open()
        super().emit(record)


def setup_logging(log_dir, level=logging.WARNING):
    """Configure root logging: monthly file + console. Idempotent.

    *level* is the threshold for both the root logger and the Werkzeug
    request logger. It defaults to WARNING so the log stays quiet; pass INFO
    (e.g. ``--log-level INFO``) to capture startup detail and request lines.
    """
    os.makedirs(log_dir, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        "%Y-%m-%d %H:%M:%S")

    root = logging.getLogger()
    root.setLevel(level)

    has_file = any(isinstance(h, MonthlyFileHandler) for h in root.handlers)
    if not has_file:
        fh = MonthlyFileHandler(log_dir)
        fh.setFormatter(fmt)
        root.addHandler(fh)

    has_console = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, MonthlyFileHandler)
        for h in root.handlers)
    if not has_console:
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        root.addHandler(ch)

    logging.getLogger("werkzeug").setLevel(level)
    return os.path.join(log_dir, "livecsv-" + time.strftime("%Y-%m") + ".log")
