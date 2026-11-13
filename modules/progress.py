"""
Progress Module
---------------
A one-line spinner shown while a long step runs: the line is redrawn several
times per second (spinning character, live elapsed time), and the terminal
cursor is hidden meanwhile so it does not blink at the end of the line.

When the output is not a terminal (redirected to a file, a pipe, a CI log),
nothing is animated: only the final line, if any, is written.
"""

import itertools
import sys
import threading
import time

_FRAMES = '|/-\\'
_HIDE_CURSOR, _SHOW_CURSOR = '\033[?25l', '\033[?25h'
_CLEAR_LINE = '\r\033[K'


class Spinner:
    """
    Redraw `\\r<frame> <text>` every `interval` seconds until stopped.

    `text` is a string or a function of the elapsed seconds returning the
    string, so the caller can show live values. Use as a context manager;
    stop() may also be called early (e.g. when the first answer word arrives).
    On stop the line is erased, unless `keep` is given: then it is replaced
    by that final text. message() prints a line above the spinner.
    """

    def __init__(self, text, interval=0.2, stream=None):
        self.text = text
        self.interval = interval
        self.stream = stream or sys.stdout
        self.start = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._tty = hasattr(self.stream, 'isatty') and self.stream.isatty()
        self._keep = None

    def _line(self):
        elapsed = time.monotonic() - self.start
        return self.text(elapsed) if callable(self.text) else f"{self.text} {elapsed:.0f}s"

    def _write(self, text):
        with self._lock:
            self.stream.write(_CLEAR_LINE + text)
            self.stream.flush()

    def message(self, text):
        """Print a full line above the spinner (it is redrawn on the next tick)."""
        with self._lock:
            self.stream.write((_CLEAR_LINE if self._tty else '') + text + '\n')
            self.stream.flush()

    def _run(self):
        for frame in itertools.cycle(_FRAMES):
            self._write(f"{frame} {self._line()}")
            if self._stop.wait(self.interval):
                break
        self._write('' if self._keep is None else self._keep + '\n')
        with self._lock:
            self.stream.write(_SHOW_CURSOR)
            self.stream.flush()

    def __enter__(self):
        self.start = time.monotonic()
        if self._tty:
            self.stream.write(_HIDE_CURSOR)
            self._thread.start()
        return self

    def stop(self, keep=None):
        """Stop the spinner; replace the line by `keep`, or erase it."""
        if self._stop.is_set():
            return
        self._keep = keep
        self._stop.set()
        if self._tty:
            self._thread.join()
        elif keep is not None:
            self.stream.write(keep + '\n')
            self.stream.flush()

    def __exit__(self, *exc):
        self.stop()
