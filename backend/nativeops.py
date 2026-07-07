# -*- coding: utf-8 -*-
"""OS-level helpers: native file dialog, open-with-default, reveal-in-folder.

``pick_file`` tries several backends in order. A backend that *runs* returns
its result (a path, or ``None`` for cancel/failure) and that result is final —
a cancel must never trigger the next backend. Only a backend that is *not
installed* raises :class:`_Unavailable`, which moves on to the next one.

Backends (Windows): PowerShell+WinForms (primary) → pywin32 → tkinter.
The PowerShell backend writes the chosen path to a temp file (UTF-8) rather
than capturing stdout, because PowerShell host output mangles non-ASCII paths.
"""

import os
import sys
import tempfile
import subprocess


class _Unavailable(Exception):
    """Raised by a backend that cannot run at all (so the next one is tried)."""


def pick_file(initial_dir=None):
    """Show a native open-file dialog and return the chosen path or ``None``."""
    if sys.platform == "win32":
        backends = (_pick_powershell, _pick_win32, _pick_tkinter)
    else:
        backends = (_pick_tkinter,)
    for fn in backends:
        try:
            return fn(initial_dir) or None
        except _Unavailable:
            continue
    return None


def _pick_powershell(initial_dir=None):
    """Windows-primary backend. Raises ``_Unavailable`` if PowerShell is absent."""
    fd, tmp = tempfile.mkstemp(suffix=".csvviewer.txt")
    os.close(fd)
    tmp_ps = tmp.replace("'", "''")
    init = "''"
    if initial_dir:
        init = "'" + initial_dir.replace("'", "''") + "'"
    # The chosen path comes from the WinForms dialog as a real .NET Unicode
    # string (never via the command line), and is written to the temp file as
    # UTF-8, so non-ASCII paths round-trip cleanly.
    # Create a hidden TopMost Form as the dialog owner so the file picker
    # surfaces above the browser window instead of slipping to the back.
    script = (
        "Add-Type -AssemblyName System.Windows.Forms\n"
        "$d = New-Object System.Windows.Forms.OpenFileDialog\n"
        "$d.Title = 'Select CSV file'\n"
        "$d.InitialDirectory = " + init + "\n"
        "$d.Filter = 'CSV / Text (*.csv;*.tsv;*.txt)|*.csv;*.tsv;*.txt|All files (*.*)|*.*'\n"
        "$d.FilterIndex = 1\n"
        "$f = New-Object System.Windows.Forms.Form\n"
        "$f.TopMost = $true\n"
        "$f.WindowState = 'Minimized'\n"
        "$f.ShowInTaskbar = $false\n"
        "$f.Show()\n"
        "$f.Hide()\n"
        "if ($d.ShowDialog($f) -eq [System.Windows.Forms.DialogResult]::OK) { "
        "Set-Content -LiteralPath '" + tmp_ps + "' -Value $d.FileName -Encoding UTF8 }\n"
        "$f.Dispose()\n"
    )
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-STA", "-Command", script],
            capture_output=True, timeout=600,
        )
    except FileNotFoundError:
        _safe_remove(tmp)
        raise _Unavailable()
    except (subprocess.TimeoutExpired, OSError):
        _safe_remove(tmp)
        return None
    try:
        with open(tmp, "r", encoding="utf-8-sig") as f:   # utf-8-sig tolerates BOM
            out = f.read().strip()
    except OSError:
        out = ""
    _safe_remove(tmp)
    return out or None


def _pick_win32(initial_dir=None):
    """pywin32 fallback. Raises ``_Unavailable`` if pywin32 is not installed."""
    try:
        import win32gui
        import win32con
    except Exception as exc:
        raise _Unavailable() from exc
    try:
        flags = (
            win32con.OFN_FILEMUSTEXIST
            | win32con.OFN_PATHMUSTEXIST
            | getattr(win32con, "OFN_EXPLORER", 0x00080000)
            | getattr(win32con, "OFN_HIDEREADONLY", 0x4)
        )
        # Win32 lpstrFilter: pairs separated by NUL, double-NUL terminated.
        result = win32gui.GetOpenFileNameW(
            InitialDir=initial_dir or "",
            Title="选择 CSV 文件 / Select CSV file",
            Filter=("CSV / Text (*.csv;*.tsv;*.txt)\x00*.csv;*.tsv;*.txt\x00"
                    "All files (*.*)\x00*.*\x00"),
            FilterIndex=1,
            Flags=flags,
        )
        if isinstance(result, (list, tuple)):
            result = result[0] if result else ""
        return result or None
    except Exception:
        return None


def _pick_tkinter(initial_dir=None):
    """Cross-platform last resort."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        path = filedialog.askopenfilename(
            initialdir=initial_dir or "",
            title="选择 CSV 文件 / Select CSV file",
            filetypes=[("CSV / Text", "*.csv *.tsv *.txt"), ("All files", "*.*")],
        )
        return path or None
    except Exception:
        return None
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def _safe_remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def open_default(path):
    """Open *path* with the OS default application."""
    try:
        os.startfile(path)  # Windows
        return True
    except (AttributeError, OSError):
        pass
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except OSError:
        return False


def reveal(path):
    """Open the containing folder, selecting *path* where supported."""
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path) or "."])
        return True
    except OSError:
        return False
